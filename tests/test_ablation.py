"""The M5 ablation: the rulings it runs under, and the nulling mechanics.

The rulings are tested for consistency with the register and the frozen
detector set, so a typo in a field name cannot quietly make a field look
unjustified or a class look undetected.
"""

from ablation import rulings
from detect.detectors import DETECTORS

DETECTOR_IDS = {d.id for d in DETECTORS}
CLASSES = {f"A{i}" for i in range(1, 11)}


def test_every_class_has_a_ruled_detector_entry():
    assert set(rulings.CLASS_DETECTOR) == CLASSES


def test_every_ruled_detector_is_in_the_frozen_set():
    for attack_class, detector_id in rulings.CLASS_DETECTOR.items():
        if attack_class in rulings.ABSENT_CLASSES:
            assert detector_id is None
        else:
            assert detector_id in DETECTOR_IDS, attack_class


def test_non_holdout_classes_use_their_own_detector():
    by_class = {d.attack_class: d.id for d in DETECTORS}
    for attack_class, detector_id in rulings.CLASS_DETECTOR.items():
        if attack_class in by_class:
            assert detector_id == by_class[attack_class], attack_class


def test_the_holdouts_use_the_catches_m4_recorded():
    assert rulings.CLASS_DETECTOR["A9"] == "d-a03"
    assert rulings.CLASS_DETECTOR["A5"] == "d-a06"


def test_every_justified_field_is_registered(fields):
    names = {f["name"] for f in fields}
    assert rulings.STATED_JUSTIFICATION <= names
    assert len(rulings.STATED_JUSTIFICATION) == 10


def test_fp_denominators_name_real_detectors():
    assert set(rulings.FP_DENOMINATOR) <= DETECTOR_IDS
    assert set(rulings.FP_DENOMINATOR.values()) <= {"all", "b1"}


def test_the_three_methodology_states_are_kept():
    assert {"X", "x", "."} <= set(rulings.CELL_CODES)
