#!/usr/bin/env python
"""Шаг 5. Лампочки на спине и звук."""

import time

import pycozmo


def main() -> int:
    with pycozmo.connect() as cli:
        print("Перебираю цвета лампочек")
        for light in (
            pycozmo.lights.red_light,
            pycozmo.lights.green_light,
            pycozmo.lights.blue_light,
            pycozmo.lights.white_light,
        ):
            cli.set_all_backpack_lights(light)
            time.sleep(0.7)
        cli.set_backpack_lights_off()

        print("Только центральная лампочка")
        cli.set_center_backpack_lights(pycozmo.lights.blue_light)
        time.sleep(1.0)
        cli.set_backpack_lights_off()

        print("Свой цвет (RGB) с мерцанием")
        custom = pycozmo.lights.Color(rgb=(255, 0, 128)).to_int16()
        cli.set_all_backpack_lights(
            pycozmo.protocol_encoder.LightState(
                on_color=custom, off_color=0,
                on_frames=10, off_frames=10,
                transition_on_frames=5, transition_off_frames=5,
            )
        )
        time.sleep(3.0)
        cli.set_backpack_lights_off()

        print("Подсветка-фонарик над камерой")
        cli.set_head_light(True)
        time.sleep(1.5)
        cli.set_head_light(False)

        print("Громкость на максимум и звук")
        cli.set_volume(50000)
        time.sleep(0.5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
