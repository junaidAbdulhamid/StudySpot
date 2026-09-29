"""Location-local temporal joins. Features never see future knowledge."""

import heapq

import numpy as np
import pandas as pd


def asof_rows(events, times, event_column, max_age_minutes, respect_knowledge=True):
    """O((events + buckets) log events); late older records cannot replace newer ones."""
    if events.empty:
        return [None] * len(times)
    events = events.copy()
    events["_known"] = events.available_at if respect_knowledge else events[event_column]
    events = events.sort_values(["_known", event_column, "id"], kind="stable")
    records = events.to_dict("records")
    heap, position, output = [], 0, []
    age = pd.Timedelta(minutes=max_age_minutes)
    for timestamp in times:
        while position < len(records) and records[position]["_known"] <= timestamp:
            row = records[position]
            if row[event_column] <= timestamp:
                heapq.heappush(heap, (-row[event_column].value, -position, row))
            position += 1
        while heap and timestamp - heap[0][2][event_column] > age:
            heapq.heappop(heap)
        output.append(heap[0][2] if heap else None)
    return output


class EventWindow:
    def __init__(self, events, event_column):
        self.frame = events.sort_values(event_column)
        self.column = event_column
        self.times = pd.DatetimeIndex(self.frame[event_column])

    def at(self, timestamp, minutes):
        # (T-window, T], evaluated exactly at T; future events in T's bucket are excluded.
        start = self.times.searchsorted(timestamp - pd.Timedelta(minutes=minutes), side="right")
        end = self.times.searchsorted(timestamp, side="right")
        rows = self.frame.iloc[start:end]
        return rows[rows.available_at <= timestamp]


def active_counts(checkins, times):
    if checkins.empty:
        return np.zeros(len(times), dtype=int)
    start = checkins.available_at
    # A late checkout changes known active state only once received; expiry was known at start.
    end = pd.concat([checkins.expires_at, checkins.checkout_available_at], axis=1).min(axis=1)
    valid = end > start
    starts = pd.DatetimeIndex(start[valid]).sort_values()
    ends = pd.DatetimeIndex(end[valid]).sort_values()
    return starts.searchsorted(times, side="right") - ends.searchsorted(times, side="right")
