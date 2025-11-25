#! /usr/bin/env python3

from enum import Enum
import time
import os

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Point32, Polygon
from lifecycle_msgs.srv import GetState
from opennav_coverage_msgs.action import NavigateCompleteCoverage
import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from geometry_msgs.msg import Point32, Polygon
from geometry_msgs.msg import PolygonStamped   # <-- add this
import xml.etree.ElementTree as ET

# Lanelet2 python
from lanelet2.io import Origin, load
from lanelet2.projection import LocalCartesianProjector


class TaskResult(Enum):
    UNKNOWN = 0
    SUCCEEDED = 1
    CANCELED = 2
    FAILED = 3


class CoverageNavigatorTester(Node):

    def __init__(self):
        super().__init__(node_name='coverage_navigator_tester')
        self.goal_handle = None
        self.result_future = None
        self.status = None
        self.feedback = None

        # Parameters
        self.declare_parameter('osm_file', '')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('origin_lat', 0.0)
        self.declare_parameter('origin_lon', 0.0)

        self.osm_file = self.get_parameter('osm_file').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        origin_lat = self.get_parameter('origin_lat').get_parameter_value().double_value
        origin_lon = self.get_parameter('origin_lon').get_parameter_value().double_value

        self.poly_pub = self.create_publisher(PolygonStamped, "lanelet_coverage_polygon", 10)


        if not self.osm_file or not os.path.exists(self.osm_file):
            self.get_logger().error(f"OSM file '{self.osm_file}' not set or does not exist")
        else:
            # For this VMB OSM, we will parse local_x/local_y manually
            self.get_logger().info(f"Parsing VMB OSM file: {self.osm_file}")
            try:
                self.osm_root = ET.parse(self.osm_file).getroot()
            except Exception as e:
                self.get_logger().error(f"Error parsing OSM: {e}")
                self.osm_root = None


        self.coverage_client = ActionClient(
            self, NavigateCompleteCoverage, 'navigate_complete_coverage')

    def destroy_node(self):
        self.coverage_client.destroy()
        super().destroy_node()

    def publish_field_polygon(self, field):
        """Publish the field polygon as PolygonStamped for visualization in RViz."""
        poly_stamped = PolygonStamped()
        poly_stamped.header.frame_id = self.frame_id
        poly_stamped.header.stamp = self.get_clock().now().to_msg()
        poly_stamped.polygon = self.toPolygon(field)
        self.poly_pub.publish(poly_stamped)
        self.get_logger().info(
            f"Published lanelet coverage polygon with {len(field)} vertices on 'lanelet_coverage_polygon'")

    def toPolygon(self, field):
        poly = Polygon()
        for coord in field:
            pt = Point32()
            pt.x = coord[0]
            pt.y = coord[1]
            pt.z = 0.0
            poly.points.append(pt)
        return poly

    def lanelet_to_field(self):
        """
        Convert the selected lanelet (left/right bounds) into a polygon field:
        left bound forward, right bound backward.
        """
        if not hasattr(self, 'lanelet') or self.lanelet is None:
            self.get_logger().error("No lanelet loaded to convert to field!")
            return []

        field = []

        self.get_logger().info(f"lanelet leftBound has {len(self.lanelet.leftBound)} points")
        self.get_logger().info(f"lanelet rightBound has {len(self.lanelet.rightBound)} points")

        # left bound forward
        for i, pt in enumerate(self.lanelet.leftBound):
            self.get_logger().info(f"left[{i}]: x={pt.x}, y={pt.y}")
            field.append([pt.x, pt.y])

        # right bound backward to close strip
        for j, pt in enumerate(reversed(self.lanelet.rightBound)):
            self.get_logger().info(f"right[{j}]: x={pt.x}, y={pt.y}")
            field.append([pt.x, pt.y])

        self.get_logger().info(f"Generated field with {len(field)} vertices from lanelet")
        return field
    
    def osm_to_field(self):
        """
        Parse the VMB-style OSM and build a polygon field from the single lanelet.
        Uses <tag k="local_x"/"local_y"> instead of lat/lon.
        """
        if self.osm_root is None:
            self.get_logger().error("OSM root is not loaded!")
            return []

        # 1) Build a dict of node id -> (x,y) from local_x/local_y
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

        # 2) Build ways: way id -> list of node ids
        ways = {}
        for way in self.osm_root.findall('way'):
            wid = way.get('id')
            nds = [nd.get('ref') for nd in way.findall('nd')]
            ways[wid] = nds

        self.get_logger().info(f"Parsed {len(ways)} ways")

        # 3) Find the lanelet relation and identify left/right way ids
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

        self.get_logger().info(f"Lanelet relation uses left way={left_way_id}, right way={right_way_id}")

        if left_way_id not in ways or right_way_id not in ways:
            self.get_logger().error("Left or right way ID not found in ways dictionary!")
            return []

        left_node_ids = ways[left_way_id]
        right_node_ids = ways[right_way_id]

        # 4) Build polygon: left way forward, right way backward
        field = []

        # left boundary in order
        for nid in left_node_ids:
            if nid not in nodes:
                self.get_logger().warn(f"Left node id {nid} not found in nodes dict!")
                continue
            x, y = nodes[nid]
            field.append([x, y])

        # right boundary in reverse order
        for nid in reversed(right_node_ids):
            if nid not in nodes:
                self.get_logger().warn(f"Right node id {nid} not found in nodes dict!")
                continue
            x, y = nodes[nid]
            field.append([x, y])

        if field and field[0] != field[-1]:
            field.append(field[0])

        self.get_logger().info(f"Generated field with {len(field)} vertices from OSM lanelet")
        return field



    def navigateCoverage(self, field):
        """Send a NavigateCompleteCoverage action request using lanelet polygon."""
        print("Waiting for 'NavigateCompleteCoverage' action server")
        while not self.coverage_client.wait_for_server(timeout_sec=1.0):
            print('"NavigateCompleteCoverage" action server not available, waiting...')

        goal_msg = NavigateCompleteCoverage.Goal()
        goal_msg.frame_id = self.frame_id
        goal_msg.polygons.append(self.toPolygon(field))

        print('Navigating coverage with field of size: ' + str(len(field)) + '...')
        send_goal_future = self.coverage_client.send_goal_async(
            goal_msg, feedback_callback=self._feedbackCallback)
        rclpy.spin_until_future_complete(self, send_goal_future)
        self.goal_handle = send_goal_future.result()

        if not self.goal_handle.accepted:
            print('Navigate Coverage request was rejected!')
            return False

        self.result_future = self.goal_handle.get_result_async()
        return True

    def isTaskComplete(self):
        """Check if the task request is complete yet."""
        if not self.result_future:
            return True
        rclpy.spin_until_future_complete(self, self.result_future, timeout_sec=0.10)
        if self.result_future.result():
            self.status = self.result_future.result().status
            if self.status != GoalStatus.STATUS_SUCCEEDED:
                print(f'Task failed with status code: {self.status}')
                return True
        else:
            # Timed out, still processing, not complete yet
            return False

        print('Task succeeded!')
        return True

    def _feedbackCallback(self, msg):
        self.feedback = msg.feedback
        return

    def getFeedback(self):
        return self.feedback

    def getResult(self):
        if self.status == GoalStatus.STATUS_SUCCEEDED:
            return TaskResult.SUCCEEDED
        elif self.status == GoalStatus.STATUS_ABORTED:
            return TaskResult.FAILED
        elif self.status == GoalStatus.STATUS_CANCELED:
            return TaskResult.CANCELED
        else:
            return TaskResult.UNKNOWN

    def startup(self, node_name='bt_navigator'):
        # Wait for BT navigator to become active
        print(f'Waiting for {node_name} to become active..')
        node_service = f'{node_name}/get_state'
        state_client = self.create_client(GetState, node_service)
        while not state_client.wait_for_service(timeout_sec=1.0):
            print(f'{node_service} service not available, waiting...')

        req = GetState.Request()
        state = 'unknown'
        while state != 'active':
            print(f'Getting {node_name} state...')
            future = state_client.call_async(req)
            rclpy.spin_until_future_complete(self, future)
            if future.result() is not None:
                state = future.result().current_state.label
                print(f'Result of get_state: {state}')
            time.sleep(2)
        return


def main():
    rclpy.init()

    navigator = CoverageNavigatorTester()
    navigator.startup()

    # Build field polygon from Lanelet2 lanelet
    field = navigator.osm_to_field()
    if not field:
        print("No field generated from lanelet, exiting.")
        return

    navigator.publish_field_polygon(field)

    navigator.navigateCoverage(field)

    i = 0
    while not navigator.isTaskComplete():
        i += 1
        feedback = navigator.getFeedback()
        if feedback and i % 5 == 0:
            eta = Duration.from_msg(
                feedback.estimated_time_remaining).nanoseconds / 1e9
            print('Estimated time of arrival: ' + '{0:.0f}'.format(eta) + ' seconds.')
        time.sleep(1)

    result = navigator.getResult()
    if result == TaskResult.SUCCEEDED:
        print('Goal succeeded!')
    elif result == TaskResult.CANCELED:
        print('Goal was canceled!')
    elif result == TaskResult.FAILED:
        print('Goal failed!')
    else:
        print('Goal has an invalid return status!')

    navigator.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
