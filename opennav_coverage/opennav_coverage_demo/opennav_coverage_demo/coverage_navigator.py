#!/usr/bin/env python3

import math
import time
import os
import xml.etree.ElementTree as ET

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration

from lifecycle_msgs.srv import GetState
from action_msgs.msg import GoalStatus

from geometry_msgs.msg import Point32, Polygon, PolygonStamped
from nav_msgs.msg import Path

from nav2_msgs.action import NavigateToPose
from opennav_coverage_msgs.action import ComputeCoveragePath


class CoverageRouteExecutor(Node):
    """
    1. Build polygon from OSM lanelet (VMB-style local_x/local_y).
    2. Call ComputeCoveragePath to get coverage nav_path.
    3. Downsample nav_path into waypoints.
    4. Send each waypoint to NavigateToPose (Nav2 does replanning around obstacles).
    """

    def __init__(self):
        super().__init__('coverage_route_executor')

        # Parameters
        self.declare_parameter('osm_file', '')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('min_goal_separation', 3.0)  # meters between waypoints

        self.osm_file = self.get_parameter('osm_file').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.min_goal_separation = self.get_parameter('min_goal_separation').get_parameter_value().double_value

        if not self.osm_file or not os.path.exists(self.osm_file):
            self.get_logger().error(f"OSM file '{self.osm_file}' not set or does not exist")
            raise SystemExit

        self.get_logger().info(f"Parsing OSM file: {self.osm_file}")
        try:
            self.osm_root = ET.parse(self.osm_file).getroot()
        except Exception as e:
            self.get_logger().error(f"Error parsing OSM: {e}")
            raise SystemExit

        # Publishers (for visualization)
        self.poly_pub = self.create_publisher(PolygonStamped, "lanelet_coverage_polygon", 10)
        self.coverage_path_pub = self.create_publisher(Path, "coverage_global_path", 10)

        # Action clients
        self.compute_cov_client = ActionClient(self, ComputeCoveragePath, 'compute_coverage_path')
        self.nav_to_pose_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Kick things off after everything has time to come up
        self.timer = self.create_timer(3.0, self.start)
        self.started = False

    # ---------- OSM → polygon (same logic you used before, but self-contained) ----------

    def osm_to_field(self):
        """
        Parse VMB-style OSM and build a polygon from the single lanelet.

        Uses tags:
          <tag k="local_x" v="..."/>
          <tag k="local_y" v="..."/>
        instead of lat/lon.
        """
        nodes = {}
        for node in self.osm_root.findall('node'):
            nid = node.get('id')
            local_x = None
            local_y = None
            for tag in node.findall('tag'):
                k = tag.get('k')
                v = tag.get('v')
                if k == 'local_x':
                    local_x = float(v)
                elif k == 'local_y':
                    local_y = float(v)
            if local_x is not None and local_y is not None:
                nodes[nid] = (local_x, local_y)
        self.get_logger().info(f"Parsed {len(nodes)} nodes with local_x/local_y")

        ways = {}
        for way in self.osm_root.findall('way'):
            wid = way.get('id')
            nds = [nd.get('ref') for nd in way.findall('nd')]
            ways[wid] = nds
        self.get_logger().info(f"Parsed {len(ways)} ways")

        lanelet_rel = None
        for rel in self.osm_root.findall('relation'):
            tags = {t.get('k'): t.get('v') for t in rel.findall('tag')}
            if tags.get('type') == 'lanelet':
                lanelet_rel = rel
                break

        if lanelet_rel is None:
            self.get_logger().error("No relation with type='lanelet' found in OSM!")
            return []

        left_way_id = None
        right_way_id = None
        for mem in lanelet_rel.findall('member'):
            role = mem.get('role')
            ref = mem.get('ref')
            if role == 'left':
                left_way_id = ref
            elif role == 'right':
                right_way_id = ref

        self.get_logger().info(f"Lanelet relation: left way={left_way_id}, right way={right_way_id}")

        if left_way_id not in ways or right_way_id not in ways:
            self.get_logger().error("Left or right way ID not found in ways dictionary!")
            return []

        left_node_ids = ways[left_way_id]
        right_node_ids = ways[right_way_id]

        field = []

        # left boundary
        for nid in left_node_ids:
            if nid not in nodes:
                self.get_logger().warn(f"Left node {nid} not found in nodes dict!")
                continue
            x, y = nodes[nid]
            field.append([x, y])

        # right boundary (reverse)
        for nid in reversed(right_node_ids):
            if nid not in nodes:
                self.get_logger().warn(f"Right node {nid} not found in nodes dict!")
                continue
            x, y = nodes[nid]
            field.append([x, y])

        # Close polygon explicitly
        if field and field[0] != field[-1]:
            field.append(field[0])

        self.get_logger().info(f"Generated field with {len(field)} vertices")
        return field

    def field_to_polygon(self, field):
        poly = Polygon()
        for coord in field:
            pt = Point32()
            pt.x = coord[0]
            pt.y = coord[1]
            pt.z = 0.0
            poly.points.append(pt)
        return poly

    def publish_field_polygon(self, field):
        msg = PolygonStamped()
        msg.header.frame_id = self.frame_id
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.polygon = self.field_to_polygon(field)
        self.poly_pub.publish(msg)
        self.get_logger().info(
            f"Published lanelet coverage polygon with {len(field)} vertices on 'lanelet_coverage_polygon'"
        )

    # ---------- Startup + state waiting ----------

    def wait_for_nav2_active(self, node_name='bt_navigator'):
        self.get_logger().info(f"Waiting for {node_name} to become active...")
        node_service = f'{node_name}/get_state'
        state_client = self.create_client(GetState, node_service)
        while not state_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'{node_service} service not available, waiting...')

        req = GetState.Request()
        state = 'unknown'
        while state != 'active':
            future = state_client.call_async(req)
            rclpy.spin_until_future_complete(self, future)
            if future.result() is not None:
                state = future.result().current_state.label
                self.get_logger().info(f'{node_name} state: {state}')
            time.sleep(1.0)

    def start(self):
        if self.started:
            return
        self.started = True
        self.timer.cancel()

        # Make sure Nav2 BT navigator is active
        self.wait_for_nav2_active('bt_navigator')

        # Build field polygon from OSM
        field = self.osm_to_field()
        if not field:
            self.get_logger().error("No field generated from OSM; exiting.")
            return

        self.publish_field_polygon(field)

        # Step 1: compute coverage path
        self.compute_and_execute_coverage(field)

    # ---------- Coverage → NavigateToPose executor ----------

    def compute_and_execute_coverage(self, field):
        # Wait for coverage server
        self.get_logger().info("Waiting for 'compute_coverage_path' action server...")
        if not self.compute_cov_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("compute_coverage_path action server not available!")
            return

        goal = ComputeCoveragePath.Goal()
        goal.use_gml_file = False
        goal.polygons_frame_id = self.frame_id
        goal.polygons.append(self.field_to_polygon(field))
        goal.generate_headland = False
        goal.generate_route = True
        goal.generate_path = True

        self.get_logger().info("Sending ComputeCoveragePath goal...")
        future = self.compute_cov_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle or not goal_handle.accepted:
            self.get_logger().error("ComputeCoveragePath goal rejected!")
            return

        result_future = goal_handle.get_result_async()
        self.get_logger().info("Waiting for ComputeCoveragePath result...")
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result

        if not result.nav_path.poses:
            self.get_logger().error("Coverage path is empty; nothing to execute.")
            return

        self.get_logger().info(
            f"Coverage path computed in {result.planning_time:.3f}s: "
            f"{len(result.nav_path.poses)} poses"
        )

        # Publish path for RViz
        path_msg = result.nav_path
        self.coverage_path_pub.publish(path_msg)

        # Downsample nav_path into waypoints
        waypoints = self.downsample_path(path_msg, self.min_goal_separation)
        self.get_logger().info(f"Downsampled to {len(waypoints)} NavigateToPose goals")

        # Execute each waypoint with NavigateToPose
        self.execute_waypoints(waypoints)

    def downsample_path(self, path: Path, min_dist: float):
        """Return a list of PoseStamped from path, separated by at least min_dist."""
        waypoints = []
        last_pose = None

        for pose_stamped in path.poses:
            if last_pose is None:
                waypoints.append(pose_stamped)
                last_pose = pose_stamped
                continue

            dx = pose_stamped.pose.position.x - last_pose.pose.position.x
            dy = pose_stamped.pose.position.y - last_pose.pose.position.y
            dist = math.hypot(dx, dy)
            if dist >= min_dist:
                waypoints.append(pose_stamped)
                last_pose = pose_stamped

        # Ensure final pose is included
        if path.poses and (not waypoints or waypoints[-1] != path.poses[-1]):
            waypoints.append(path.poses[-1])

        return waypoints

    def execute_waypoints(self, waypoints):
        self.get_logger().info("Waiting for NavigateToPose action server...")
        if not self.nav_to_pose_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("navigate_to_pose action server not available!")
            return

        for i, pose in enumerate(waypoints):
            self.get_logger().info(
                f"Sending NavigateToPose {i+1}/{len(waypoints)} to "
                f"({pose.pose.position.x:.2f}, {pose.pose.position.y:.2f})"
            )

            goal = NavigateToPose.Goal()
            goal.pose = pose

            send_goal_future = self.nav_to_pose_client.send_goal_async(goal)
            rclpy.spin_until_future_complete(self, send_goal_future)
            goal_handle = send_goal_future.result()

            if not goal_handle or not goal_handle.accepted:
                self.get_logger().warn(f"NavigateToPose goal {i+1} rejected; skipping.")
                continue

            result_future = goal_handle.get_result_async()
            # Wait for result (with timeout)
            self.get_logger().info("Waiting for NavigateToPose result...")
            rclpy.spin_until_future_complete(self, result_future)
            result = result_future.result()

            status = result.status
            if status == GoalStatus.STATUS_SUCCEEDED:
                self.get_logger().info(f"Waypoint {i+1} succeeded.")
            elif status == GoalStatus.STATUS_ABORTED:
                self.get_logger().warn(f"Waypoint {i+1} aborted; skipping to next.")
            elif status == GoalStatus.STATUS_CANCELED:
                self.get_logger().warn(f"Waypoint {i+1} canceled; skipping to next.")
            else:
                self.get_logger().warn(
                    f"Waypoint {i+1} returned unknown status {status}; skipping to next."
                )

        self.get_logger().info("Finished executing all coverage waypoints.")


def main(args=None):
    rclpy.init(args=args)
    node = CoverageRouteExecutor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
