"""Tests for the heartbeat dictionary."""

from time import sleep

from dbeats import HeartbeatDictionary


def test_update_creates_alive_client():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    alive = d.alive_clients()
    assert len(alive) == 1
    assert alive[0][0] == '1.2.3.4'


def test_update_does_not_double_count():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    d.update('1.2.3.4')
    assert len(d.alive_clients()) == 1


def test_reap_marks_stale_dead():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    sleep(0.05)
    dead = d.reap(timeout=0)
    assert len(dead) == 1
    assert dead[0][0] == '1.2.3.4'
    assert d.alive_clients() == []


def test_reap_only_returns_each_death_once():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    sleep(0.05)
    d.reap(timeout=0)
    second = d.reap(timeout=0)
    assert second == []


def test_reap_keeps_fresh_clients_alive():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    dead = d.reap(timeout=60)
    assert dead == []
    assert len(d.alive_clients()) == 1


def test_recovery_after_death():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    sleep(0.05)
    d.reap(timeout=0)
    assert d.drain_recovered() == []
    d.update('1.2.3.4')
    recovered = d.drain_recovered()
    assert len(recovered) == 1
    assert recovered[0][0] == '1.2.3.4'
    assert len(d.alive_clients()) == 1


def test_drain_recovered_clears_list():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    sleep(0.05)
    d.reap(timeout=0)
    d.update('1.2.3.4')
    d.drain_recovered()
    assert d.drain_recovered() == []


def test_first_beat_does_not_record_recovery():
    d = HeartbeatDictionary()
    d.update('1.2.3.4')
    assert d.drain_recovered() == []


def test_multiple_clients_tracked_independently():
    d = HeartbeatDictionary()
    d.update('1.1.1.1')
    d.update('2.2.2.2')
    sleep(0.05)
    d.reap(timeout=0)
    d.update('1.1.1.1')
    recovered = d.drain_recovered()
    assert len(recovered) == 1
    assert recovered[0][0] == '1.1.1.1'
    assert d.alive_clients()[0][0] == '1.1.1.1'
