"""CLI helper to print merged config."""

from pyhocon import HOCONConverter

from super.config import get_app_conf


def main() -> None:
    conf = get_app_conf(app="generate_powers")
    assert conf.super_hero == "Buggs Bunny", "app config should override project super_hero"
    assert conf.get("garbage") == "zevel adom", "developer config should be included"
    print(HOCONConverter.to_hocon(conf))


if __name__ == "__main__":
    main()
