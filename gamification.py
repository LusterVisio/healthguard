import os
import json
import datetime

class Gamification:
    def __init__(self):
        self.data = {
            'points': 0,
            'daily_breaks': 0,
            'current_streak': 0,
            'last_break_date': None,
            'challenges': {
                'weekly_points': {'target': 500, 'progress': 0, 'completed': False},
                'weekly_breaks': {'target': 10, 'progress': 0, 'completed': False}
            },
            'last_reset': None
        }
        self.load_data()
        self.check_weekly_reset()

    def load_data(self):
        try:
            with open('gamification.json', 'r') as f:
                loaded_data = json.load(f)
                for date_field in ['last_break_date', 'last_reset']:
                    if loaded_data.get(date_field):
                        loaded_data[date_field] = datetime.datetime.strptime(
                            loaded_data[date_field], '%Y-%m-%d').date()
                self.data.update(loaded_data)
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_data()

    def save_data(self):
        data_to_save = self.data.copy()
        for date_field in ['last_break_date', 'last_reset']:
            if data_to_save.get(date_field):
                data_to_save[date_field] = data_to_save[date_field].isoformat()
        with open('gamification.json', 'w') as f:
            json.dump(data_to_save, f)

    def check_weekly_reset(self):
        if not self.data['last_reset'] or \
                (datetime.date.today() - self.data['last_reset']).days >= 7:
            self.reset_weekly_challenges()

    def reset_weekly_challenges(self):
        self.data['challenges']['weekly_points']['progress'] = 0
        self.data['challenges']['weekly_points']['completed'] = False
        self.data['challenges']['weekly_breaks']['progress'] = 0
        self.data['challenges']['weekly_breaks']['completed'] = False
        self.data['last_reset'] = datetime.date.today()
        self.save_data()

    def add_points(self, points):
        self.data['points'] += points
        if not self.data['challenges']['weekly_points']['completed']:
            self.data['challenges']['weekly_points']['progress'] += points
            if self.data['challenges']['weekly_points']['progress'] >= \
                    self.data['challenges']['weekly_points']['target']:
                self.data['challenges']['weekly_points']['completed'] = True
                self.data['points'] += 100
        self.save_data()

    def record_break(self):
        today = datetime.date.today()
        if self.data['last_break_date'] != today:
            if self.data['last_break_date'] and \
                    (today - self.data['last_break_date']).days == 1:
                self.data['current_streak'] += 1
            else:
                self.data['current_streak'] = 1
            self.data['last_break_date'] = today
            self.data['daily_breaks'] = 1
        else:
            self.data['daily_breaks'] += 1

        if not self.data['challenges']['weekly_breaks']['completed']:
            self.data['challenges']['weekly_breaks']['progress'] += 1
            if self.data['challenges']['weekly_breaks']['progress'] >= \
                    self.data['challenges']['weekly_breaks']['target']:
                self.data['challenges']['weekly_breaks']['completed'] = True
                self.data['points'] += 50
        self.save_data()