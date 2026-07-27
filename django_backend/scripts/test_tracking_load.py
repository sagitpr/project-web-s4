"""
Load Test: Delivery Tracking WebSocket Events
Simulates multiple concurrent delivery_update WebSocket events
to verify the system can handle burst traffic without degradation.

Usage:
    python scripts/test_tracking_load.py [--count 100] [--concurrent 10]
"""

import os
import sys
import time
import json
import random
import statistics
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from orders.views import notify_delivery_update

User = get_user_model()

DELIVERY_STATUSES = [
    'diproses_penjual', 'menunggu_penjemputan', 'kurir_menjemput',
    'dalam_perjalanan', 'pesanan_diterima', 'dibatalkan',
]

RESULTS = {'success': 0, 'failed': 0, 'latencies': [], 'errors': []}
RESULTS_LOCK = threading.Lock()


def fire_delivery_update(user_id, order_num):
    start = time.perf_counter()
    try:
        notify_delivery_update(
            user_id=user_id,
            order_id=order_num,
            order_number=f'LOAD-TEST-{order_num}',
            delivery_status=random.choice(DELIVERY_STATUSES),
            tracking_number=f'TRK{random.randint(10000, 99999)}',
            courier=random.choice(['GoSend', 'GrabExpress', 'Maxim', 'Antar Sendiri']),
        )
        elapsed = (time.perf_counter() - start) * 1000
        with RESULTS_LOCK:
            RESULTS['success'] += 1
            RESULTS['latencies'].append(elapsed)
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        with RESULTS_LOCK:
            RESULTS['failed'] += 1
            RESULTS['errors'].append(str(e)[:100])
            RESULTS['latencies'].append(elapsed)


def worker_thread(user_id, event_ids):
    for eid in event_ids:
        fire_delivery_update(user_id, eid)


def run_load_test(total_events=100, concurrent=10):
    print(f"\n{'='*60}")
    print(f"  DELIVERY TRACKING LOAD TEST")
    print(f"  Total events: {total_events} | Workers: {concurrent}")
    print(f"{'='*60}")

    user, _ = User.objects.get_or_create(
        email='loadtest@warungio.io',
        defaults={
            'username': 'loadtest_user', 'full_name': 'Load Test User',
            'is_verified': True, 'is_active': True, 'role': 'buyer',
        },
    )
    print(f"  User: {user.email} (ID: {user.id})")

    event_ids = list(range(1, total_events + 1))
    chunk_size = max(1, total_events // concurrent)
    chunks = [event_ids[i:i + chunk_size] for i in range(0, len(event_ids), chunk_size)]

    threads = []
    start_time = time.perf_counter()

    for chunk in chunks:
        if not chunk:
            continue
        t = threading.Thread(target=worker_thread, args=(user.id, chunk))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.perf_counter() - start_time
    latencies = RESULTS['latencies']
    success = RESULTS['success']
    failed = RESULTS['failed']
    errors = RESULTS['errors']

    print(f"\n{'-'*60}")
    print(f"  RESULTS")
    print(f"{'-'*60}")
    print(f"  Total time:      {total_time:.2f}s")
    print(f"  Events/sec:      {total_events / total_time:.1f}")
    print(f"  Success:         {success}")
    print(f"  Failed:          {failed}")
    if latencies:
        print(f"  Latency (ms):")
        print(f"    Min:           {min(latencies):.1f}")
        print(f"    Max:           {max(latencies):.1f}")
        print(f"    Avg:           {statistics.mean(latencies):.1f}")
        if len(latencies) > 1:
            print(f"    Median:        {statistics.median(latencies):.1f}")
        if len(latencies) >= 20:
            print(f"    P95:           {sorted(latencies)[int(len(latencies)*0.95)]:.1f}")
        if len(latencies) >= 100:
            print(f"    P99:           {sorted(latencies)[int(len(latencies)*0.99)]:.1f}")
    if errors:
        print(f"\n  Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"    - {err}")

    assert failed == 0, f"{failed} events failed!"
    assert total_events / total_time > 10, f"Throughput: {total_events / total_time:.1f} (min 10)"
    print(f"\n  [PASS] All events delivered successfully ({success}/{total_events})")
    print(f"{'='*60}\n")

    return {
        'total_events': total_events, 'total_time': total_time,
        'events_per_sec': total_events / total_time,
        'success': success, 'failed': failed,
        'latency_ms': {
            'min': min(latencies) if latencies else 0,
            'max': max(latencies) if latencies else 0,
            'avg': statistics.mean(latencies) if latencies else 0,
            'median': statistics.median(latencies) if len(latencies) > 1 else 0,
            'p95': sorted(latencies)[int(len(latencies)*0.95)] if len(latencies) >= 20 else 0,
            'p99': sorted(latencies)[int(len(latencies)*0.99)] if len(latencies) >= 100 else 0,
        },
    }


def verify_channel_layer():
    print(f"\n{'-'*60}")
    print(f"  Channel Layer Verification")
    print(f"{'-'*60}")
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            print(f"  [FAIL] Channel layer is None - check CHANNEL_LAYERS")
            return False
        async_to_sync(channel_layer.send)('test_channel', {'type': 'test.message'})
        print(f"  [OK] Channel layer send")
        result = async_to_sync(channel_layer.receive)('test_channel')
        assert result == {'type': 'test.message'}
        print(f"  [OK] Channel layer receive")
        return True
    except Exception as e:
        print(f"  [FAIL] Channel layer error: {e}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Delivery Tracking Load Test')
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--concurrent', type=int, default=10)
    args = parser.parse_args()

    channel_ok = verify_channel_layer()
    if not channel_ok:
        print("\n  Channel layer unavailable - skipping load test.")
        sys.exit(1)

    result = run_load_test(args.count, args.concurrent)

    output_path = os.path.join(os.path.dirname(__file__), '..', 'benchmark_tracking.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  Results exported to: benchmark_tracking.json")
