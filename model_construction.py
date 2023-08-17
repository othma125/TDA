from math import ceil

import pulp as p
from data_objects import track, location, train
from input_data import data


class math_model:
    def __init__(self, input_data: data):
        self.__inputs: data = input_data
        self.__model: p.LpProblem = p.LpProblem("train_dispatching", p.LpMinimize)
        self.__travel_arc_variables: dict = {}
        self.__waiting_arc_variables: dict = {}
        obj = 0
        self.__delay = 0
        for t in self.__inputs.trains:
            departure_time: int = t.departure_time if t.departure_time % self.__inputs.time_step == 0 else self.__inputs.time_step * ceil(
                t.departure_time / self.__inputs.time_step)
            max_time_stamp: int = departure_time + 2 * (t.arrival_time - departure_time)
            for time in range(departure_time, max_time_stamp, self.__inputs.time_step):
                for tr_id, tr in enumerate(t.tracks):
                    tr_arc: travel_arc = travel_arc(t, time, tr_id)
                    self.__travel_arc_variables[tr_arc.get_unique_key()] = tr_arc.get_binary_variable()
                if len(t.route) > 2:
                    for loc in t.route:
                        if loc == t.arrival_location or loc == t.departure_location:
                            continue
                        w_arc: waiting_arc = waiting_arc(t, time, loc)
                        self.__waiting_arc_variables[w_arc.get_unique_key()] = w_arc.get_binary_variable_for_waiting()

            # objective function
            for time in range(departure_time, max_time_stamp, self.__inputs.time_step):
                for tr_id, tr in enumerate(t.tracks):
                    if tr.arrival_location == t.arrival_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr_id)
                        time_stamp: int = time + tr.traveled_time(self.__inputs.trains_speed)
                        obj += self.__travel_arc_variables[tr_arc.get_unique_key()] * (
                                    time_stamp - t.arrival_time) * t.category
                        self.__delay += self.__travel_arc_variables[tr_arc.get_unique_key()] * (
                                    time_stamp - t.arrival_time)

            constraint_value2 = 0
            constraint_value3 = 0
            for time in range(departure_time, max_time_stamp, self.__inputs.time_step):
                for tr_id, tr in enumerate(t.tracks):
                    if tr.departure_location == t.departure_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr_id)
                        uni_key: str = tr_arc.get_unique_key()
                        if time < t.departure_time:
                            self.__model += self.__travel_arc_variables[uni_key] == 0
                        if time > t.departure_time + self.__inputs.time_step:
                            self.__model += self.__travel_arc_variables[uni_key] == 0
                        constraint_value2 += self.__travel_arc_variables[uni_key]
                    if tr.arrival_location == t.arrival_location:
                        tr_arc: travel_arc = travel_arc(t, time, tr_id)
                        uni_key: str = tr_arc.get_unique_key()
                        constraint_value3 += self.__travel_arc_variables[uni_key]
            # constraint 2
            self.__model += constraint_value2 == 1
            # constraint 3
            self.__model += constraint_value3 == 1

            # constraint 4
            departure: int = departure_time
            for tr_id, tr in enumerate(t.tracks):
                if tr.arrival_location == t.arrival_location:
                    break
                next_tr = None
                for tr_id2, tr2 in enumerate(t.tracks):
                    if tr2.departure_location == tr.arrival_location:
                        next_tr = tr_id2
                        break
                arrival: int = departure + tr.traveled_time(self.__inputs.trains_speed)
                arrival += 0 if t.arrival_location == tr.arrival_location or t.category == 1 else self.__inputs.trains_waiting_time_in_stations
                arrival = self.__inputs.time_step * ceil(
                    arrival / self.__inputs.time_step) if arrival % self.__inputs.time_step > 0 else arrival
                arrival_time_stamp: int = arrival
                departure_time_stamp: int = departure
                while departure_time_stamp < max_time_stamp:
                    tr_arc: travel_arc = travel_arc(t, departure_time_stamp, tr_id)
                    uni_key: str = tr_arc.get_unique_key()
                    sum1 = self.__travel_arc_variables[uni_key]
                    if len(t.route) > 2:
                        w_arc: waiting_arc = waiting_arc(t, arrival_time_stamp - self.__inputs.time_step, tr.arrival_location)
                        uni_key: str = w_arc.get_unique_key()
                        sum1 += self.__waiting_arc_variables[uni_key] if uni_key in self.__waiting_arc_variables else 0
                    sum2 = 0
                    if len(t.route) > 2:
                        w_arc: waiting_arc = waiting_arc(t, arrival_time_stamp, tr.arrival_location)
                        uni_key: str = w_arc.get_unique_key()
                        sum2 += self.__waiting_arc_variables[uni_key] if uni_key in self.__waiting_arc_variables.keys() else 0
                    tr_arc: travel_arc = travel_arc(t, arrival_time_stamp, next_tr)
                    uni_key: str = tr_arc.get_unique_key()
                    sum2 += self.__travel_arc_variables[uni_key] if uni_key in self.__travel_arc_variables.keys() else 0
                    self.__model += sum1 == sum2
                    arrival_time_stamp += self.__inputs.time_step
                    departure_time_stamp += self.__inputs.time_step
                departure = arrival

        # waiting sites capacity constraint
        for key in self.__waiting_arc_variables.keys():
            w_arc: waiting_arc = waiting_arc.get_waiting_arc(self.__inputs, key)
            constraint_value = self.__waiting_arc_variables[key]
            for t in self.__inputs.trains:
                if t == w_arc.train and len(t.route) <= 2:
                    continue
                w_arc2: waiting_arc = waiting_arc(t, w_arc.time_stamp, w_arc.waiting_station)
                uni_key: str = w_arc2.get_unique_key()
                if uni_key in self.__waiting_arc_variables.keys():
                    constraint_value += self.__waiting_arc_variables[uni_key]
            self.__model += constraint_value <= w_arc.waiting_station.capacity

        # conflicts constraint
        for key in self.__travel_arc_variables.keys():
            tr_arc: travel_arc = travel_arc.get_travel_arc(self.__inputs, key)
            uni_key: str = tr_arc.get_unique_key()
            travel_time: int = tr_arc.traveled_track.traveled_time(self.__inputs.trains_speed)
            arrival: int = tr_arc.time_stamp + travel_time
            arrival += 0 if tr_arc.traveled_track.arrival_location == tr_arc.train.arrival_location or tr_arc.train.category == 1 else self.__inputs.trains_waiting_time_in_stations
            arrival = arrival if arrival % self.__inputs.time_step == 0 else self.__inputs.time_step * ceil(
                arrival / self.__inputs.time_step)
            for t in self.__inputs.trains:
                if t == tr_arc.train:
                    continue
                for time in range(tr_arc.time_stamp, arrival, self.__inputs.time_step):
                    tr_arc2: travel_arc = travel_arc(t, time, tr_arc.track_id)
                    uni_key2: str = tr_arc2.get_unique_key()
                    if uni_key2 in self.__travel_arc_variables.keys():
                        self.__model += 1 - self.__travel_arc_variables[uni_key] >= self.__travel_arc_variables[
                            uni_key2]
                    if tr_arc.traveled_track.is_single_track:
                        inv_tr: track = tr_arc.traveled_track.get_inverse()
                        tr_arc2: travel_arc = travel_arc(t, time, inv_tr.traveled_by(t))
                        uni_key2: str = tr_arc2.get_unique_key()
                        if uni_key2 in self.__travel_arc_variables.keys():
                            self.__model += 1 - self.__travel_arc_variables[uni_key] >= self.__travel_arc_variables[uni_key2]
                departure_time: int = t.departure_time if t.departure_time % self.__inputs.time_step == 0 else self.__inputs.time_step * ceil(
                    t.departure_time / self.__inputs.time_step)
                if departure_time >= tr_arc.time_stamp:
                    continue
                for time in range(departure_time, tr_arc.time_stamp, self.__inputs.time_step):
                    if tr_arc.time_stamp - time < arrival - tr_arc.time_stamp:
                        tr_arc2: travel_arc = travel_arc(t, time, tr_arc.track_id)
                        uni_key2: str = tr_arc2.get_unique_key()
                        if uni_key2 in self.__travel_arc_variables.keys():
                            self.__model += 1 - self.__travel_arc_variables[uni_key] >= self.__travel_arc_variables[
                                uni_key2]
                    if tr_arc.traveled_track.is_single_track:
                        inv_tr: track = tr_arc.traveled_track.get_inverse()
                        if tr_arc.time_stamp - time < arrival - tr_arc.time_stamp:
                            tr_arc2: travel_arc = travel_arc(t, time, inv_tr.traveled_by(t))
                            uni_key2: str = tr_arc2.get_unique_key()
                            if uni_key2 in self.__travel_arc_variables.keys():
                                self.__model += 1 - self.__travel_arc_variables[uni_key] >= self.__travel_arc_variables[uni_key2]

        self.__model += obj

    def solve(self):
        self.__model.solve()
        status: str = p.LpStatus[self.__model.status]
        print(f'Result status = {status}')
        if status == 'Infeasible':
            return
        print(f'Objective function value = {p.value(self.__model.objective)}')
        print(f'Total delay of trains = {p.value(self.__delay)}')
        for key, x in self.__travel_arc_variables.items():
            if p.value(x) == 1:
                tr_arc = travel_arc.get_travel_arc(self.__inputs, key)
                time_stamp: int = tr_arc.time_stamp + tr_arc.traveled_track.traveled_time(self.__inputs.trains_speed)
                if tr_arc.traveled_track.departure_location == tr_arc.train.departure_location:
                    print(f'Train {tr_arc.train} travel from {tr_arc.train.departure_location} to {tr_arc.train.arrival_location}')
                print(f'departure from {tr_arc.traveled_track.departure_location} at {toTimeFormat(tr_arc.time_stamp)},', end='')
                print(f' arrival to {tr_arc.traveled_track.arrival_location} at {toTimeFormat(time_stamp)}')
                if tr_arc.traveled_track.arrival_location == tr_arc.train.arrival_location:
                    print(f'Scheduled arrival time for train {tr_arc.train.index + 1} is {toTimeFormat(tr_arc.train.arrival_time)}')


class travel_arc:
    def __init__(self, trn: train, time: int, tr_id: int):
        self.train = trn
        self.track_id: int = tr_id
        self.time_stamp: int = time
        self.traveled_track: track = self.train.tracks[self.track_id]

    def get_unique_key(self) -> str:
        return "t".join((str(self.time_stamp), str(self.track_id), str(self.train.index)))

    def get_binary_variable(self):
        return p.LpVariable(self.get_unique_key(),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)

    @classmethod
    def get_travel_arc(cls, input_data: data, s: str):
        l = s.split('t')
        return cls(input_data.trains[int(l[2])], int(l[0]), int(l[1]))


class waiting_arc:
    def __init__(self, trn: train, time: int, loc: location):
        self.train = trn
        self.time_stamp: int = time
        self.waiting_station: location = loc

    def get_unique_key(self) -> str:
        return "w".join((str(self.time_stamp), str(self.waiting_station.index), str(self.train.index)))

    def get_binary_variable_for_waiting(self):
        return p.LpVariable(self.get_unique_key(),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)

    @classmethod
    def get_waiting_arc(cls, input_data: data, s: str):
        l = s.split('w')
        # print(l[1])
        # print(l[0])
        # print(l[2])
        # print(len(input_data.locations))
        return cls(input_data.trains[int(l[2])], int(l[0]), input_data.locations[int(l[1])])


def toTimeFormat(time: int) -> str:
    hour = time // 60
    s = ("0" if hour < 10 else "") + str(hour) + ":"
    minutes = time % 60
    s += ("0" if minutes < 10 else "") + str(minutes)
    return s
