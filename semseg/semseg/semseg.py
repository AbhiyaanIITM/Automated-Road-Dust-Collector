#! /usr/bin/python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import torch
from fastsam import FastSAM, FastSAMPrompt
from PIL import Image as PILImage
import numpy as np
import cv2
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
class Semseg(Node):
    def __init__(self):
        super().__init__('semseg_node')
        self.declare_parameter('model_path', './weights/FastSAM.pt')
        self.declare_parameter('conf', 0.4)
        self.declare_parameter('iou', 0.9)
        self.declare_parameter('imgsz', 1024)
        self.declare_parameter('retina', True)
        self.declare_parameter('device', 'cuda' if torch.cuda.is_available() else 'cpu')

        model_path = self.get_parameter('model_path').value
        self.device = self.get_parameter('device').value

        self.bridge = CvBridge()
        self.get_logger().info(f'Loading FastSAM model from {model_path}...')
        self.model = FastSAM(model_path)
        self.get_logger().info('Model loaded successfully.')

        self.sub = self.create_subscription(
            Image,
            '/zed/zed_node/rgb/image_rect_color',
            self.image_callback,
            10
        )
        self.pub = self.create_publisher(Image, '/segmentation_mask', 10)
        self.get_logger().info('FastSAM segmentation node initialized.')

    def image_callback(self, msg):
        
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        pil_image = PILImage.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        
        # Run inference
        results = self.model(
            pil_image,
            device=self.device,
            retina_masks=self.get_parameter('retina').value,
            imgsz=self.get_parameter('imgsz').value,
            conf=self.get_parameter('conf').value,
            iou=self.get_parameter('iou').value
        )
        
        
        # Process prompts
        prompt_process = FastSAMPrompt(pil_image, results, device=self.device)
        ann = prompt_process.everything_prompt()
        
        bboxes = None
        points = None
        point_label = None
        img = prompt_process.plot(
            annotations=ann,
            bboxes = bboxes,
            points = points,
            output_path=None,
            point_label = point_label,
            withContours=False,
            better_quality=False,
        )
        ros_mask = self.bridge.cv2_to_imgmsg(img, encoding='rgb8')
        ros_mask.header = msg.header
        self.pub.publish(ros_mask)
       

def main(args=None):
    rclpy.init(args=args)
    node = Semseg()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()