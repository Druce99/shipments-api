import re

from shipments_api.domain.tracking import generate_tracking_number


def test_generate_tracking_number_has_expected_format() -> None:
    number = generate_tracking_number()

    assert re.fullmatch(r"TRK-[0-9A-F]{12}", number)


def test_generate_tracking_number_differs_between_calls() -> None:
    numbers = {generate_tracking_number() for _ in range(1000)}

    assert len(numbers) == 1000
