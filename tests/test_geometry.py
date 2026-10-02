from flashcards_app.geometry import sphere_positions


def test_positions_are_deterministic_and_inside_sphere():
    ids = ["one", "two", "three"]
    first = sphere_positions(ids, seed=7)
    second = sphere_positions(ids, seed=7)
    assert first == second
    assert all(point.x**2 + point.y**2 + point.z**2 <= 1 for point in first)
