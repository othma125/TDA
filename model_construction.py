import pulp as p
from data_objects import track, location, train
from input_data import data


class math_model:
    def __init__(self, input_data: data):
        self.inputs: data = input_data
        self.model: p.LpProblem = p.LpProblem("train_dispatching", p.LpMinimize)
        departure_time = min(t.departure_time for t in self.inputs.trains)
        departure_time: int = departure_time if departure_time % self.inputs.time_step == 0 else self.inputs.time_step + self.inputs.time_step * (
                departure_time // self.inputs.time_step)
        arrival_time = max(t.arrival_time for t in self.inputs.trains)
        self.travel_arc_variable: dict = {}
        self.waiting_arc_variable: dict = {}
        self.arrival_arc_variable: dict = {}
        obj = 0
        for t in self.inputs.trains:
            for time in range(departure_time, departure_time + 2 * (arrival_time - departure_time) + self.inputs.time_step, self.inputs.time_step):
                for tr in t.tracks:
                    tr_arc: travel_arc = travel_arc(t, time, tr)
                    self.travel_arc_variable[tr_arc.get_unique_key()] = tr_arc.get_binary_variable()
                for loc in t.path:
                    if loc == t.arrival_location or loc == t.departure_location:
                        continue
                    w_arc: waiting_arc = waiting_arc(t, time, loc)
                    self.waiting_arc_variable[w_arc.get_unique_key()] = w_arc.get_binary_variable_for_waiting()
                    self.arrival_arc_variable[w_arc.get_unique_key()] = w_arc.get_binary_variable_for_arrival()
            # objective function
            for key, x in self.travel_arc_variable.items():
                if key[3] == t.index and key[2] == t.arrival_location.index:
                    tr: track = track(self.inputs.locations[key[1]], self.inputs.locations[key[2]])
                    time_stamp: int = key[0] + tr.traveled_time(self.inputs.trains_speed)
                    obj += x * (time_stamp - t.arrival_time)
            # constraint 2
            self.model += p.lpSum(x for key, x in self.travel_arc_variable.items() if
                                  key[3] == t.index and key[1] == t.departure_location.index and
                                  key[0] >= t.departure_time) == 1
            self.model += p.lpSum(x for key, x in self.travel_arc_variable.items() if
                                  key[3] == t.index and int(key[1]) == t.departure_location.index and
                                  key[0] < t.departure_time) == 0
            # constraint 3
            self.model += p.lpSum(x for key, x in self.travel_arc_variable.items() if key[3] == t.index and
                                  key[2] == t.arrival_location.index) == 1
            # constraint 4
            for key, x in self.travel_arc_variable.items():
                if key[3] == t.index and key[2] != t.arrival_location.index:
                    sum1 = x
                    tr: track = track(self.inputs.locations[key[1]], self.inputs.locations[key[2]])
                    time_stamp: int = key[0] + tr.traveled_time(self.inputs.trains_speed)
                    time_stamp += self.inputs.trains_waiting_time_in_stations if tr.arrival_location != t.arrival_location and not tr.arrival_location.is_siding else 0
                    if tr.arrival_location != t.arrival_location and time_stamp % self.inputs.time_step > 0:
                        for next_arc_key, z in self.arrival_arc_variable.items():
                            if next_arc_key[2] == t.index and next_arc_key[1] == key[2] and self.inputs.time_step * (time_stamp // self.inputs.time_step) == next_arc_key[0]:
                                self.model += x == z
                                break
                        time_stamp = self.inputs.time_step + self.inputs.time_step * (time_stamp // self.inputs.time_step)
                    for next_arc_key, y in self.waiting_arc_variable.items():
                        if next_arc_key[2] == t.index and next_arc_key[1] == key[2] and time_stamp <= next_arc_key[0]:
                            sum1 += y
                    sum2 = 0
                    for next_arc_key, y in self.travel_arc_variable.items():
                        if next_arc_key[3] == t.index and next_arc_key[1] == key[2] and time_stamp <= next_arc_key[0]:
                            sum2 += y
                            break
                    for next_arc_key, z in self.waiting_arc_variable.items():
                        if next_arc_key[2] == t.index and next_arc_key[1] == key[2] and time_stamp <= next_arc_key[0]:
                            sum2 += z
                    self.model += sum1 == sum2
        # objective function
        self.model += obj
        # # constraint 5
        for key1, x in self.waiting_arc_variable.items():
            constraint_value = 0
            c = False
            for key2, y in self.waiting_arc_variable.items():
                if key1[1] == key2[1] and key1[0] == key2[0]:
                    constraint_value += y
                    c = True
            for key2, y in self.arrival_arc_variable.items():
                if key1[1] == key2[1] and key1[0] == key2[0]:
                    constraint_value += y
                    c = True
            if c:
                self.model += constraint_value <= self.inputs.locations[key1[1]].capacity
        # constraint 6
        for key1, x in self.travel_arc_variable.items():
            tr: track = track(self.inputs.locations[key1[1]], self.inputs.locations[key1[2]])
            if tr.is_single_track:
                constraint_value = x
                c = False
                for key2, y in self.travel_arc_variable.items():
                    if key1[1] == key2[2] and key1[2] == key2[1] and key1[0] < key2[0] and key2[0] - key1[0] <= tr.traveled_time():
                        constraint_value += y
                        c = True
                if c:
                    self.model += constraint_value <= 1
        # constraint 7
        for key1, x in self.travel_arc_variable.items():
            constraint_value = x
            c = False
            for key2, y in self.travel_arc_variable.items():
                if key1[1] == key2[1] and key1[2] == key2[2] and key1[0] < key2[0] and key2[0] - key1[0] <= self.inputs.safety_time:
                    constraint_value += y
                    c = True
            if c:
                self.model += constraint_value <= 1

    def solve(self):
        self.model.solve()
        print(p.LpStatus[self.model.status])
        print(p.value(self.model.objective))
        for key, x in self.travel_arc_variable.items():
            t: train = self.inputs.trains[key[3]]
            tr: track = track(self.inputs.locations[key[1]], self.inputs.locations[key[2]])
            if p.value(x) == 1:
                print(f'Train with index = {t.index + 1} travel in track = {tr}')
                print(
                    f'Departure time = {key[0]}, arrival time = {key[0] + tr.traveled_time(self.inputs.trains_speed)}')
                if tr.arrival_location == t.arrival_location:
                    print(f'Scheduled arrival time for train {t.index + 1} is {t.arrival_time}')


class travel_arc:
    def __init__(self, trn: train, time: int, tr: track):
        self.time_stamp: int = time
        self.traveled_track: track = tr
        self.train = trn

    def get_unique_key(self):
        return self.time_stamp, self.traveled_track.departure_location.index, self.traveled_track.arrival_location.index, self.train.index

    def get_binary_variable(self):
        return p.LpVariable("t".join((str(self.time_stamp), str(self.traveled_track.departure_location.index), str(
            self.traveled_track.arrival_location.index), str(self.train.index))),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)


class waiting_arc:
    def __init__(self, trn: train, time: int, loc: location):
        self.time_stamp: int = time
        self.waiting_station: location = loc
        self.train = trn

    def get_unique_key(self):
        return self.time_stamp, self.waiting_station.index, self.train.index

    def get_binary_variable_for_waiting(self):
        return p.LpVariable("w".join((str(self.time_stamp), str(self.waiting_station.index), str(self.train.index))),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)

    def get_binary_variable_for_arrival(self):
        return p.LpVariable("a".join((str(self.time_stamp), str(self.waiting_station.index), str(self.train.index))),
                            lowBound=0,
                            upBound=1,
                            cat=p.LpBinary)
