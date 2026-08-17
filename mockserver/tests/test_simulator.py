import time

from prusa.connect.printer import const

from app.simulator import PrintSimulator


def test_xl_tracks_toolheads_and_consumes_filament_on_finish():
    states = []
    consumed = []
    simulator = PrintSimulator(
        lambda state, source: states.append((state, source)),
        simulation_speed=1000,
        tool_slots=[0, 1, 2, 3, 4],
        chamber_supported=False,
        on_finished=consumed.append,
    )

    simulator.start(
        "/usb/test.gcode",
        estimated_duration_s=10,
        used_tools=[0, 2],
        tool_targets_c={0: 24, 2: 24},
        target_bed_c=24,
        filament_used_g={0: 2.0, 2: 1.0},
    )
    deadline = time.monotonic() + 2
    while simulator.running and time.monotonic() < deadline:
        time.sleep(0.01)

    assert not simulator.running
    assert len(simulator.snapshot.toolheads) == 5
    assert simulator.snapshot.phase == "FINISHED"
    assert simulator.snapshot.progress_percent == 100
    assert simulator.snapshot.active_tool is None
    assert consumed == [{0: 2.0, 2: 1.0}]
    assert states[-1][0] == const.State.FINISHED


def test_coreone_exposes_chamber_temperature():
    simulator = PrintSimulator(
        lambda state, source: None,
        simulation_speed=1,
        tool_slots=[0],
        chamber_supported=True,
    )

    assert simulator.snapshot.chamber_temperature_c == 24
    assert set(simulator.snapshot.toolheads) == {0}
