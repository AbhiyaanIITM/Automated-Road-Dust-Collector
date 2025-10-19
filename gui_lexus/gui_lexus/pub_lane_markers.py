import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
import yaml
import os

class MinimalPublisher(Node):

    def __init__(self):
        super().__init__('lanelet_publisher')
        self.publisher_ = self.create_publisher(MarkerArray, "/lanelet", 10)
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0
        self.get_logger().info("Started")
        self.topic_content = self.load_yaml_file()

    def load_yaml_file(self):
        pkg_name = 'gui_lexus'
        pkg_dir = os.popen('/bin/bash -c "cd && source /usr/share/colcon_cd/function/colcon_cd.sh && colcon_cd %s && pwd"' % pkg_name).read().strip()
        self.get_logger().info(pkg_dir)        
        with open(pkg_dir+'/resource/zalazone_uni_track_marker.yaml') as file:
            try:
                topic_content = yaml.load(file, Loader=yaml.FullLoader)
                #print(topic_content)
                self.get_logger().info("Loaded yaml file")
            except yaml.YAMLError as exc:
                self.get_logger().info(exc)
            return topic_content

    def timer_callback(self):
        msg = MarkerArray()
        for m in self.topic_content["markers"]:
            #msg.markers.header.frame_id = "map"
            marker = Marker()
            marker.header.frame_id = m["header"]["frame_id"]
            marker.ns = m["ns"]
            marker.id = m["id"]
            marker.type = m["type"]
            marker.action = m["action"]
            marker.pose.position.x = m["pose"]["position"]["x"]
            marker.pose.position.y = m["pose"]["position"]["y"]
            marker.pose.position.z = m["pose"]["position"]["z"]
            marker.pose.orientation.x = m["pose"]["orientation"]["x"]
            marker.pose.orientation.y = m["pose"]["orientation"]["y"]
            marker.pose.orientation.z = m["pose"]["orientation"]["z"]
            marker.pose.orientation.w = m["pose"]["orientation"]["w"]
            marker.scale.x = m["scale"]["x"]
            marker.scale.y = m["scale"]["y"]
            marker.scale.z = m["scale"]["z"]
            marker.color.a = m["color"]["a"]
            marker.color.r = m["color"]["r"]
            marker.color.g = m["color"]["g"]
            marker.color.b = m["color"]["b"]
            marker.frame_locked = m["frame_locked"]
            marker.mesh_use_embedded_materials = m["mesh_use_embedded_materials"]
            for c in m["colors"]:
                # https://github.com/jkk-research/colors
                color = ColorRGBA()
                color.a = 1.0 #c["a"]
                color.r = 0.78 #c["r"]
                color.g = 0.90 #c["g"]
                color.b = 0.79 #c["b"]
                marker.colors.append(color)
            for p in m["points"]:
                point = Point()
                point.x = p["x"]
                point.y = p["y"]
                point.z = p["z"]
                marker.points.append(point)
            msg.markers.append(marker)

        self.publisher_.publish(msg)
        #self.get_logger().info('Publishing: "%d"' % self.i)
        self.i += 1


def main(args=None):
    rclpy.init(args=args)

    lanelet_publisher = MinimalPublisher()

    rclpy.spin(lanelet_publisher)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    lanelet_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()