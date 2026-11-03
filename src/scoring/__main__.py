from .climate import OUT, fetch_climate
from .engine import grade_all
from .features import build_features
from .validate import validate


def main():
    if not OUT.exists():
        fetch_climate()
    features = build_features()
    grades = grade_all(features)
    validate(features, grades)


if __name__ == "__main__":
    main()
