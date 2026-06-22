# planner_node.py

import math
import heapq
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped

# Same-package import in ROS2 Python
from robotaksi_planning.track_graph import TRACK_NODES, TRACK_EDGES


class AStarPlannerNode(Node):
    def __init__(self):
        super().__init__('robotaksi_planner_node')
        
        self.path_pub = self.create_publisher(Path, '/planlanan_rota', 10)
        
        # TEKNOFEST Yarışma Görev Sırası: Başlangıç -> Görev 2 -> Park
        # (Araç zaten Görev 1 noktasında doğduğu için rota 1'den başlar)
        self.mission_checkpoints = [1, 10, 12] 
        
        # 2 saniyede bir yayınla (Controller yakalasın diye latching mantığı)
        self.timer = self.create_timer(2.0, self.publish_master_plan)
        self.get_logger().info("A* Planner Node başlatıldı. Rota hesaplanıyor...")

    def heuristic(self, node_a, node_b):
        x1, y1 = TRACK_NODES[node_a]
        x2, y2 = TRACK_NODES[node_b]
        return math.hypot(x1 - x2, y1 - y2)

    def a_star_search(self, start_id, goal_id):
        open_set = []
        heapq.heappush(open_set, (0, start_id))
        
        came_from = {}
        g_score = {n: float('inf') for n in TRACK_NODES}
        g_score[start_id] = 0
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if current == goal_id:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_id)
                path.reverse()
                return path
                
            for neighbor in TRACK_EDGES.get(current, []):
                tentative_g = g_score[current] + self.heuristic(current, neighbor)
                
                if tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self.heuristic(neighbor, goal_id)
                    heapq.heappush(open_set, (f_score, neighbor))
                    
        return []

    def publish_master_plan(self):
        full_node_sequence = []
        
        # Checkpoint'leri uç uca ekle
        for i in range(len(self.mission_checkpoints) - 1):
            start = self.mission_checkpoints[i]
            goal = self.mission_checkpoints[i + 1]
            sub_path = self.a_star_search(start, goal)
            
            if not sub_path:
                self.get_logger().error(f"ROTA BULUNAMADI: {start} -> {goal}")
                return
                
            # Birleşim yerlerindeki tekrar eden düğümleri sil (örn: [1,2,3] + [3,4] -> [1,2,3,4])
            if full_node_sequence:
                sub_path = sub_path[1:]
            full_node_sequence.extend(sub_path)

        # Node ID listesini PoseStamped mesajlarına çevir
        path_msg = Path()
        path_msg.header.frame_id = 'odom'
        path_msg.header.stamp = self.get_clock().now().to_msg()
        
        for node_id in full_node_sequence:
            pose = PoseStamped()
            pose.header = path_msg.header
            pose.pose.position.x = float(TRACK_NODES[node_id][0])
            pose.pose.position.y = float(TRACK_NODES[node_id][1])
            pose.pose.position.z = 0.0
            path_msg.poses.append(pose)
            
        self.path_pub.publish(path_msg)
        self.get_logger().info(f"Master Plan Yayınlandı! Toplam Waypoint: {len(path_msg.poses)}")


def main(args=None):
    rclpy.init(args=args)
    node = AStarPlannerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()