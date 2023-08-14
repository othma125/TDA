from data_objects import train, track, location


class data:
    def __init__(self, file_name: str):
        """
        Input file reader method
        :param file_name:
        """
        self.time_step: int = 5  # minutes
        self.trains: list = []
        with open("instances\\" + file_name, "r") as file:
            if file_name.split('.')[-1] == 'csv':
                self.trains_speed: int = 1
                self.trains_waiting_time_in_stations: int = 1
                self.locations: dict = {}
                for line in file:
                    row = line.split(',')
                    if row[0] == '' and row[1] == '':
                        continue
                    # print(row)
                    if row[1] == 'Train Name':
                        new_train = True
                        new_locations = False
                        continue
                    elif new_train:
                        new_train = False
                        category = 1 if int(row[1]) > 6000 else 2
                    if row[0] == 'SNo':
                        new_locations = True
                        tracks: list = []
                        route: list = []
                        continue
                    elif new_locations:
                        station_name = row[2]
                        if all(key != station_name for key in self.locations.keys()):
                            try:
                                station_type = station_name.split()[-1]
                                capacity = 1 if station_type == 'staj' or station_type == 'ukr' else 3
                            except IndexError:
                                capacity = 3
                            loc: location = location([str(len(self.locations) + 1), '0', '0', str(capacity), 'siding'])
                            loc.name = station_name
                            self.locations[station_name] = loc
                        if len(route) > 0:
                            tr: track = track(route[-1], self.locations[station_name])
                            h, m = row[4].split(':')
                            setattr(tr, 'travel_time', int(h) * 60 + int(m) - departure_time)
                            tracks.append(tr)
                        route.append(self.locations[station_name])
                        if row[5] != 'Destination':
                            h, m = row[5].split(':')
                            departure_time: int = int(h) * 60 + int(m)
                            if row[4] == 'Source':
                                train_departure_time = departure_time
                        else:
                            h, m = row[4].split(':')
                            train_arrival_time: int = int(h) * 60 + int(m)
                            # print(f'{train_departure_time = }')
                            # print(f'{train_arrival_time = }')
                            # for tr in tracks:
                            #     print(tr)
                            # for r in route:
                            #     print(r)
                            trn: train = train(len(self.trains), train_departure_time, train_arrival_time, category, tracks, route)
                            self.trains.append(trn)
                            new_locations = False
                self.trains_count: int = len(self.trains)
                self.stations_count: int = len(self.locations)
                # print(self.locations.keys())
                self.locations: list = [loc for loc in self.locations.values()]
                print(f"{self.trains_count = }")
                print(f"{self.stations_count = }")
                # quit()
            else:
                line = file.readline().split()
                self.stations_count: int = int(line[0])
                self.locations = [location(file.readline().split()) for _ in range(self.stations_count)]
                line = file.readline().split()
                self.trains_count: int = int(line[0])
                print(f"{self.trains_count = }")
                print(f"{self.stations_count = }")
                self.trains_speed: int = int(line[1])
                self.trains_waiting_time_in_stations: int = int(line[2])
                for t in range(self.trains_count):
                    line = file.readline().split()
                    category: int = int(line[1])
                    n: int = len(line)
                    departure: int = 0
                    time = line[2].split(':')
                    departure += int(time[0]) * 60
                    departure += int(time[1])
                    route: list[location] = [self.locations[int(line[i]) - 1] for i in range(3, n)]
                    if len(route) < 2:
                        raise ValueError('train route must contains at least two stop stations')
                    tracks = []
                    arrival: int = departure
                    n: int = len(route)
                    for i in range(n - 1):
                        tr = track(route[i], route[i + 1])
                        arrival += tr.traveled_time(self.trains_speed)
                        if not route[i].is_siding:
                            arrival += self.trains_waiting_time_in_stations if i > 0 else 0
                        tracks.append(tr)
                    self.trains.append(train(t, departure, arrival, category, tracks, route))
