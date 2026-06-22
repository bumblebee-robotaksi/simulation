# track_graph.py

"""
TEKNOFEST Robotaksi Pist Topolojisi (Gazebo /odom koordinatları)
"""

TRACK_NODES = {
    # --- Üst Yatay Yol (Row 12: y = 23.975) ---
    1: (5.00, 23.975),      # Görev 1 (Yolcu Alma / Start bölgesi)
    2: (12.04, 23.975),     # Kesişim: Üst Yol & Kolon 1
    3: (20.72, 23.975),     # Kesişim: Üst Yol & Kolon 2
    4: (30.065, 23.975),    # Kesişim: Üst Yol & Kolon 3
    5: (39.50, 23.975),     # Kesişim: Üst Yol & Doğu (Sağ) Yolu

    # --- Alt Yatay Yol (Row 23: y = 12.425) ---
    6: (12.04, 12.425),     # Kesişim: Alt Yol & Kolon 1
    7: (20.72, 12.425),     # Kesişim: Alt Yol & Kolon 2 (Rotonda girişi)
    8: (30.065, 12.425),    # Kesişim: Alt Yol & Kolon 3
    9: (39.50, 12.425),     # Kesişim: Alt Yol & Doğu (Sağ) Yolu

    # --- Uç / Görev Noktaları ---
    10: (20.72, 25.50),     # Görev 2 (Kolon 2'nin en kuzey ucu)
    11: (39.50, 24.745),    # park_giris_noktasi
    12: (40.60, 24.70),     # nihai park cebi (park_slot_3)
}

# Çift yönlü (Undirected) bağlantı listesi
TRACK_EDGES = {
    1: [2],
    2: [1, 3, 6],
    3: [2, 4, 7, 10],
    4: [3, 5, 8],
    5: [4, 9, 11],
    6: [2, 7],
    7: [3, 6, 8],
    8: [4, 7, 9],
    9: [5, 8],
    10: [3],
    11: [5, 12],
    12: [11]
}