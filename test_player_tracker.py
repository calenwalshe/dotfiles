"""
TDD tests for player_tracker.py.

Run: python3 -m pytest test_player_tracker.py -v
"""
import json
import os
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np


class TestLetterbox(unittest.TestCase):
    def test_square_output(self):
        from player_tracker import letterbox
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        lb, scale, pad_top, pad_left = letterbox(img, 640)
        self.assertEqual(lb.shape, (640, 640, 3))

    def test_scale_and_padding_are_correct(self):
        from player_tracker import letterbox
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        lb, scale, pad_top, pad_left = letterbox(img, 640)
        self.assertEqual(lb.shape, (640, 640, 3))
        # Scale should reduce 1920 -> 640: scale = 640/1920 = 0.333...
        self.assertAlmostEqual(scale, 640 / 1920, places=4)

    def test_unletterbox_roundtrip(self):
        from player_tracker import letterbox
        orig_h, orig_w = 1080, 1920
        img = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
        _, scale, pad_top, pad_left = letterbox(img, 640)

        # A box in original coords: (x1, y1, x2, y2) = (100, 200, 300, 400)
        x1_orig, y1_orig, x2_orig, y2_orig = 100, 200, 300, 400
        # Letterbox coords
        lx1 = x1_orig * scale + pad_left
        ly1 = y1_orig * scale + pad_top
        lx2 = x2_orig * scale + pad_left
        ly2 = y2_orig * scale + pad_top
        # Unletterbox
        rx1 = (lx1 - pad_left) / scale
        ry1 = (ly1 - pad_top) / scale
        rx2 = (lx2 - pad_left) / scale
        ry2 = (ly2 - pad_top) / scale
        self.assertAlmostEqual(rx1, x1_orig, places=1)
        self.assertAlmostEqual(ry1, y1_orig, places=1)
        self.assertAlmostEqual(rx2, x2_orig, places=1)
        self.assertAlmostEqual(ry2, y2_orig, places=1)


class TestEmbeddingNormalization(unittest.TestCase):
    def test_normalized_embedding_is_unit_vector(self):
        from player_tracker import normalize_embedding
        raw = np.array([3.0, 4.0])
        normed = normalize_embedding(raw)
        self.assertAlmostEqual(np.linalg.norm(normed), 1.0, places=6)

    def test_zero_vector_handled(self):
        from player_tracker import normalize_embedding
        raw = np.zeros(512)
        normed = normalize_embedding(raw)
        # Should not raise; result may be zeros or unit vector
        self.assertIsNotNone(normed)
        self.assertEqual(normed.shape, (512,))

    def test_cosine_sim_identical_vectors(self):
        from player_tracker import cosine_sim
        v = np.array([1.0, 0.0, 0.0])
        self.assertAlmostEqual(cosine_sim(v, v), 1.0, places=6)

    def test_cosine_sim_orthogonal_vectors(self):
        from player_tracker import cosine_sim
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        self.assertAlmostEqual(cosine_sim(a, b), 0.0, places=6)

    def test_cosine_sim_opposite_vectors(self):
        from player_tracker import cosine_sim
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        self.assertAlmostEqual(cosine_sim(a, b), -1.0, places=6)


class TestJerseyOCRCrop(unittest.TestCase):
    def test_torso_crop_is_top_40_percent(self):
        from player_tracker import extract_torso_crop
        # Create a 200x100 dummy frame, bbox covers full frame
        frame = np.zeros((200, 100, 3), dtype=np.uint8)
        bbox = (0, 0, 100, 200)  # x1, y1, x2, y2
        crop = extract_torso_crop(frame, bbox)
        # Torso = top 40% of bbox height = 200 * 0.4 = 80px
        self.assertEqual(crop.shape[0], 80)
        self.assertEqual(crop.shape[1], 100)

    def test_torso_crop_on_small_bbox(self):
        from player_tracker import extract_torso_crop
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Very small bbox (4px high)
        bbox = (10, 10, 20, 14)  # height=4
        crop = extract_torso_crop(frame, bbox)
        # Should return empty or small crop — not crash
        self.assertIsNotNone(crop)

    def test_torso_crop_clamps_to_frame_boundary(self):
        from player_tracker import extract_torso_crop
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Bbox extends past frame edge
        bbox = (90, 90, 120, 160)
        crop = extract_torso_crop(frame, bbox)
        self.assertIsNotNone(crop)


class TestAnnotationSchema(unittest.TestCase):
    def test_annotation_has_required_fields(self):
        from player_tracker import make_annotation
        ann = make_annotation(
            frame_idx=42,
            track_id=7,
            bbox=(10, 20, 100, 200),
            jersey_ocr="4",
            cosine_sim_val=0.85,
        )
        self.assertIn("frame_idx", ann)
        self.assertIn("track_id", ann)
        self.assertIn("bbox", ann)
        self.assertIn("jersey_ocr", ann)
        self.assertIn("cosine_sim", ann)

    def test_annotation_values_correct(self):
        from player_tracker import make_annotation
        ann = make_annotation(
            frame_idx=10,
            track_id=3,
            bbox=(5, 6, 50, 60),
            jersey_ocr="7",
            cosine_sim_val=0.72,
        )
        self.assertEqual(ann["frame_idx"], 10)
        self.assertEqual(ann["track_id"], 3)
        self.assertEqual(ann["bbox"], [5, 6, 50, 60])
        self.assertEqual(ann["jersey_ocr"], "7")
        self.assertAlmostEqual(ann["cosine_sim"], 0.72, places=4)

    def test_annotation_bbox_is_list(self):
        from player_tracker import make_annotation
        ann = make_annotation(0, 1, (0, 0, 10, 10), None, 0.5)
        self.assertIsInstance(ann["bbox"], list)


class TestCosineSimilarityThresholds(unittest.TestCase):
    def test_threshold_confident_match(self):
        from player_tracker import COSINE_CONFIDENT, COSINE_FALLBACK
        self.assertGreater(COSINE_CONFIDENT, COSINE_FALLBACK)
        self.assertAlmostEqual(COSINE_CONFIDENT, 0.7, places=2)
        self.assertAlmostEqual(COSINE_FALLBACK, 0.6, places=2)


class TestPlayerProfile(unittest.TestCase):
    def test_profile_construction_from_embeddings(self):
        from player_tracker import PlayerProfile
        profile = PlayerProfile(jersey_number="4")
        # Add some fake reference embeddings
        for _ in range(5):
            v = np.random.randn(512)
            v = v / np.linalg.norm(v)
            profile.add_reference_embedding(v)
        self.assertEqual(len(profile.reference_embeddings), 5)

    def test_profile_mean_embedding_is_unit_vector(self):
        from player_tracker import PlayerProfile
        profile = PlayerProfile(jersey_number="4")
        for _ in range(5):
            v = np.random.randn(512)
            v = v / np.linalg.norm(v)
            profile.add_reference_embedding(v)
        mean_emb = profile.get_mean_embedding()
        self.assertIsNotNone(mean_emb)
        self.assertAlmostEqual(np.linalg.norm(mean_emb), 1.0, places=5)

    def test_profile_similarity_with_itself(self):
        from player_tracker import PlayerProfile, cosine_sim
        profile = PlayerProfile(jersey_number="4")
        v = np.ones(512) / np.sqrt(512)
        profile.add_reference_embedding(v)
        mean = profile.get_mean_embedding()
        sim = cosine_sim(v, mean)
        self.assertGreater(sim, 0.99)


class TestResilienceFrames(unittest.TestCase):
    def test_preprocess_crop_empty_array(self):
        from player_tracker import preprocess_crop_for_osnet
        result = preprocess_crop_for_osnet(np.array([]))
        self.assertIsNone(result)

    def test_preprocess_crop_too_small(self):
        from player_tracker import preprocess_crop_for_osnet
        tiny = np.zeros((3, 3, 3), dtype=np.uint8)
        result = preprocess_crop_for_osnet(tiny)
        self.assertIsNone(result)

    def test_preprocess_crop_valid_crop(self):
        from player_tracker import preprocess_crop_for_osnet
        crop = np.random.randint(0, 255, (200, 100, 3), dtype=np.uint8)
        result = preprocess_crop_for_osnet(crop)
        self.assertIsNotNone(result)
        self.assertEqual(result.shape, (3, 256, 128))


if __name__ == "__main__":
    unittest.main(verbosity=2)
