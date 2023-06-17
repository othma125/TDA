from math import ceil

import pulp as p
from data_objects import track, location, train
from input_data import data


class math_model:
    def __init__(self, input_data: data):
        self.inputs: data = input_data
        self.model: p.LpProblem = p.LpProblem("train_dispatching", p.LpMinimize)
        self.travel_arc_variables: dict = {}
        self.waiting_arc_variables: dict = {}
        obj = 0
        for t in self.inputs.trains:
            departure_time: int = t.departure_time if t.departure_time % self.inputs.time_step == 0 else self.inputs.time_step * ceil(t.departure_time / self.inputs.time_step)
            max_time_stamp: int = departure_time + 2 * (t.arrival_time - departure_time)
            for time in range(departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    tr_arc: travel_arc = travel_arc(t, time, tr)
                    self.travel_arc_variables["t".join(tr_arc.get_unique_key())] = tr_arc.get_binary_variable()
                for loc in t.route:
                    if loc == t.arrival_location or loc == t.departure_location:
                        continue
                    w_arc: waiting_arc = waiting_arc(t, time, loc)
                    self.waiting_arc_variables["w".join(w_arc.get_unique_key())] = w_arc.get_binary_variable_for_waiting()

            # objective function
            for time in range(departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    if tr.arrival_location == t.arrival_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr)
                        time_stamp: int = time + tr.traveled_time(self.inputs.trains_speed)
                        obj += self.travel_arc_variables['t'.join(tr_arc.get_unique_key())] * (time_stamp - t.arrival_time) * t.category

            constraint_value2 = constraint_value3 = 0
            for time in range(departure_time, max_time_stamp, self.inputs.time_step):
                for tr in t.tracks:
                    if tr.departure_location == t.departure_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr)
                        uni_key: str = 't'.join(tr_arc.get_unique_key())
                        constraint_value2 += self.travel_arc_variables[uni_key]
                        if time == departure_time:
                            self.model += self.travel_arc_variables[uni_key] == 1
                    elif tr.arrival_location == t.arrival_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr)
                        uni_key: str = 't'.join(tr_arc.get_unique_key())
                        constraint_value3 += self.travel_arc_variables[uni_key]
            # constraint 2
            self.model += constraint_value2 == 1
            # constraint 3
            self.model += constraint_value3 == 1

            # constraint 4
            departure: int = departure_time
            for tr in t.tracks:
                if tr.arrival_location == t.arrival_location:
                    break
                next_tr: track = None
                for tr2 in t.tracks:
                    if tr2.departure_location == tr.arrival_location:
                        next_tr = tr2
                        break
                arrival: int = departure + tr.traveled_time(self.inputs.trains_speed)
                arrival += 0 if tr.arrival_location.is_siding or t.arrival_location == tr.arrival_location else self.inputs.trains_waiting_time_in_stations
                arrival = self.inputs.time_step * ceil(arrival / self.inputs.time_step) if arrival % self.inputs.time_step > 0 else arrival
                arrival_time_stamp: int = arrival
                departure_time_stamp: int = departure
                while departure_time_stamp < max_time_stamp:
                    tr_arc: travel_arc = travel_arc(t, departure_time_stamp, tr)
                    uni_key: str = 't'.join(tr_arc.get_unique_key())
                    sum1 = self.travel_arc_variables[uni_key]
                    w_arc: waiting_arc = waiting_arc(t, arrival_time_stamp - self.inputs.time_step, tr.arrival_location)
                    uni_key: str = 'w'.join(w_arc.get_unique_key())
                    sum1 += self.waiting_arc_variables[uni_key] if uni_key in self.waiting_arc_variables else 0
                    sum2 = 0
                    w_arc: waiting_arc = waiting_arc(t, arrival_time_stamp, tr.arrival_location)
                    uni_key: str = 'w'.join(w_arc.get_unique_key())
                    sum2 += self.waiting_arc_variables[uni_key] if uni_key in self.waiting_arc_variables.keys() else 0
                    tr_arc: travel_arc = travel_arc(t, arrival_time_stamp, next_tr)
                    uni_key: str = 't'.join(tr_arc.get_unique_key())
                    sum2 += self.travel_arc_variables[uni_key] if uni_key in self.travel_arc_variables.keys() else 0
                    self.model += sum1 == sum2
                    arrival_time_stamp += self.inputs.time_step
                    departure_time_stamp += self.inputs.time_step
                departure = arrival

        # waiting sites capacity constraint
        for key in self.waiting_arc_variables.keys():
            w_arc: waiting_arc = get_waiting_arc(self.inputs, key)
            constraint_value = self.waiting_arc_variables[key]
            for t in self.inputs.trains:
                if t == w_arc.train:
                    continue
                w_arc2: waiting_arc = waiting_arc(t, w_arc.time_stamp, w_arc.waiting_station)
                uni_key: str = 'w'.join(w_arc2.get_unique_key())
                if uni_key in self.waiting_arc_variables.keys():
                    constraint_value += self.waiting_arc_variables[uni_key]
            self.model += constraint_value <= w_arc.waiting_station.capacity

        # conflicts constraint
        for key in self.travel_arc_variables.keys():
            tr_arc: travel_arc = get_travel_arc(self.inputs, key)
            uni_key: str = "t".join(tr_arc.get_unique_key())
            travel_time: int = tr_arc.traveled_track.traveled_time(self.inputs.trains_speed)
            arrival: int = tr_arc.time_stamp + travel_time
            arrival += 0 if tr_arc.traveled_track.arrival_location == tr_arc.train.arrival_location or tr_arc.traveled_track.arrival_location.is_siding else self.inputs.trains_waiting_time_in_stations
            arrival = arrival if arrival % self.inputs.time_step == 0 else self.inputs.time_step * ceil(arrival / self.inputs.time_step)
            for t in self.inputs.trains:
                if t == tr_arc.train:
                    continue
                for time in range(tr_arc.time_stamp, arrival, self.inputs.time_step):
                    tr_arc2: travel_arc = travel_arc(t, time, tr_arc.traveled_track)
                    uni_key2: str = "t".join(tr_arc2.get_unique_key())
                    if uni_key2 in self.travel_arc_variables.keys():
                        self.model += 1 - self.travel_arc_variables[uni_key] >= self.travel_arc_variables[uni_key2]
                    if tr_arc.traveled_track.is_single_track:
                        inv_tr: track = tr_arc.traveled_track.get_inverse()
                        tr_arc2: travel_arc = travel_arc(t, time, inv_tr)
                        uni_key2: str = "t".join(tr_arc2.get_unique_key())
                        if uni_key2 in self.travel_arc_variables.keys():
                            self.model += 1 - self.travel_arc_variables[uni_key] >= self.travel_arc_variables[uni_key2]
                departure_time: int = t.departure_time if t.departure_time % self.inputs.time_step == 0 else self.inputs.time_step * ceil(t.departure_time / self.inputs.time_step)
                if departure_time >= tr_arc.time_stamp:
                    continue
                for time in range(departure_time, tr_arc.time_stamp, self.inputs.time_step):
                    if tr_arc.time_stamp - time < arrival - tr_arc.time_stamp:
                        tr_arc2: travel_arc = travel_arc(t, time, tr_arc.traveled_track)
                        uni_key2: str = "t".join(tr_arc2.get_unique_key())
                        if uni_key2 in self.travel_arc_variables.keys():
                            self.model += 1 - self.travel_arc_variables[uni_key] >= self.travel_arc_variables[uni_key2]
                    if tr_arc.traveled_track.is_single_track:
                        inv_tr: track = tr_arc.traveled_track.get_inverse()
                        if tr_arc.time_stamp - time < arrival - tr_arc.time_stamp:
                            tr_arc2: travel_arc = travel_arc(t, time, inv_tr)
                            uni_key2: str = "t".join(tr_arc2.get_unique_key())
                            if uni_key2 in self.travel_arc_variables.keys():
                                self.model += 1 - self.travel_arc_variables[uni_key] >= self.travel_arc_variables[uni_key2]

        self.model += obj

    def solve(self):
        self.model.solve()
        print(f'Result status = {p.LpStatus[self.model.status]}')
        print(f'Objective function value = {p.value(self.model.objective)}')
        delay: int = 0
        for key, x in self.travel_arc_variables.items():
            if p.value(x) != 1:
                continue
            tr_arc = get_travel_arc(self.inputs, key)
            if tr_arc.train.arrival_location == tr_arc.traveled_track.arrival_location:
                time_stamp: int = tr_arc.time_stamp + tr_arc.traveled_track.traveled_time(self.inputs.trains_speed)
                delay += (time_stamp - tr_arc.train.arrival_time)
        print(f'Total delay of trains = {delay}')
        for key, x in self.travel_arc_variables.items():
            if p.value(x) == 1:
                tr_arc = get_travel_arc(self.inputs, key)
                time_stamp: int = tr_arc.time_stamp + tr_arc.traveled_track.traveled_time(self.inputs.trains_speed)
                if tr_arc.traveled_track.departure_location == tr_arc.train.departure_location:
                    print(f'Train {tr_arc.train} travel from {tr_arc.train.departure_location} to {tr_arc.train.arrival_location}')
                print(
                    f'departure from {tr_arc.traveled_track.departure_location.index + 1} at {toTimeFormat(tr_arc.time_stamp)},'
                    f' arrival to {tr_arc.traveled_track.arrival_location.index + 1} at {toTimeFormat(time_stamp)}')
                if tr_arc.traveled_track.arrival_location == tr_arc.train.arrival_location:
                    print(f'Scheduled arrival time for train {tr_arc.train.index + 1} is {toTimeFormat(tr_arc.train.arrival_time)}')


class travel_arc:
    def __init__(self, trn: train, time: int, tr: track):
        self.train = trn
        self.time_stamp: int = time
        self.traveled_track: track = tr

    def get_unique_key(self) -> tuple:
        return str(self.time_stamp), str(self.traveled_track.departure_location.index), str(
            self.traveled_track.arrival_location.index), str(self.train.index)

    def get_binary_variable(self):
        return p.LpVariable("t".join(self.get_unique_key()),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)


class waiting_arc:
    def __init__(self, trn: train, time: int, loc: location):
        self.train = trn
        self.time_stamp: int = time
        self.waiting_station: location = loc

    def get_unique_key(self) -> tuple:
        return str(self.time_stamp), str(self.waiting_station.index), str(self.train.index)

    def get_binary_variable_for_waiting(self):
        return p.LpVariable("w".join(self.get_unique_key()),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)

    def get_binary_variable_for_arrival(self):
        return p.LpVariable("a".join(self.get_unique_key()),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)


def get_travel_arc(input_data: data, s: str) -> travel_arc:
    l = s.split('t')
    return travel_arc(input_data.trains[int(l[3])], int(l[0]), track(input_data.locations[int(l[1])], input_data.locations[int(l[2])]))


def get_waiting_arc(input_data: data, s: str) -> waiting_arc:
    l = s.split('w')
    return waiting_arc(input_data.trains[int(l[2])], int(l[0]), input_data.locations[int(l[1])])


def toTimeFormat(time: int) -> str:
    hour = time // 60
    s = ("0" if hour < 10 else "") + str(hour) + ":"
    minutes = time % 60
    s += ("0" if minutes < 10 else "") + str(minutes)
    return s
