# track_graph.py

"""
TEKNOFEST Robotaksi Pist Topolojisi (Gazebo /odom koordinatları)
"""

TRACK_NODES = {
    1: (2.0,  0.0),
    2: (10.0, 0.0),
    3: (22.0, 0.0),   # engele yakin, hala duzde
    4: (23.0, 1.5),   # son anda sola don
    5: (30.0, 1.5),   # engeli gec
    6: (35.0, 0.0),   # merkeze don
    7: (50.0, 0.0),   # hedef
}

TRACK_EDGES = {
    1: [2],
    2: [1, 3],
    3: [2, 4],
    4: [3, 5],
    5: [4, 6],
    6: [5, 7],
    7: [6],
}