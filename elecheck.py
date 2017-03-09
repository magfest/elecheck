#!/usr/bin/env python3
import sys
import csv
import json
from collections import Counter

PAST_YEARS_ELIGIBLE = [
    "Mag2016",
    "Labs2016",
]


class Attendee:
    def __init__(self, id, placeholder, first_name, last_name, email, birthdate,
                 badge_num, badge_type, badge_status, ribbon, can_spam,
                 staffing, nonshift_hours, past_years, hotel_eligible, **kwargs):
        self.id = id
        self.placeholder = (placeholder == 'True')
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.birthdate = birthdate
        self.badge_num = int(badge_num) if badge_num else None
        self.badge_type = badge_type
        self.badge_status = badge_status
        self.ribbon = ribbon
        self.can_spam = (can_spam == 'True')
        self.staffing = (staffing == 'True')
        self.nonshift_hours = float(nonshift_hours)
        self.past_years = past_years and json.loads(past_years) or []
        self.hoteL_eligible = (hotel_eligible == 'True')
        self.shifts = []

    def eligible_past_years(self):
        return [y for y in self.past_years if (y["year"] in PAST_YEARS_ELIGIBLE)]

    def worked_two_events(self):
        return len(self.eligible_past_years()) > 0

    def eligible_before(self):
        return any((y["worked_hours"] + y["nonshift_hours"] >= 18 for y in self.eligible_past_years()))

    def percent_worked(self):
        return len([s for s in self.shifts if s.worked]) / len(self.shifts)

    def worked_hours(self):
        return sum((shift.job.hours() for shift in self.shifts if shift.worked))

    def maybe_worked_hours(self):
        # This counts hours that have been marked off as though they were worked, in case someone
        # would be eligible but their hours just haven't been marked off
        return sum((shift.job.hours() for shift in self.shifts if shift.worked or shift.worked is None))

    def eligible(self):
        return self.worked_hours() >= 18

    def maybe_eligible(self):
        # Will return True if someone could be eligible due to unmarked hours
        return self.maybe_worked_hours() >= 18

    def review(self):
        return not self.eligible() and self.maybe_eligible() \
        and (not self.eligible_before() or not self.worked_two_events())


class Job:
    def __init__(self, id, type, name, description, location, start_time,
                 duration, weight, slots, restricted, extra15):
        self.id = id
        self.type = type
        self.name = name
        self.description = description
        self.location = location
        self.start_time = start_time
        self.duration = float(duration) # hours
        self.weight = float(weight)
        self.slots = slots
        self.restricted = (restricted == 'True')
        self.extra15 = (extra15 == 'True')

    def hours(self):
        return (self.duration + (.25 if self.extra15 else 0)) * self.weight


class Shift:
    def __init__(self, id, job, attendee, worked, rating, comment):
        self.id = id
        self.job = job
        self.attendee = attendee
        # Yes => True, No => False, not yet set => None
        self.worked = (worked == "This shift was worked" or (None if worked == "SELECT A STATUS" else False))
        self.raw_worked = worked
        self.rating = rating
        self.comment = comment


def load_attendees(filename):
    res = {}
    with open(filename, newline='') as f:
        attendee_reader = csv.DictReader(f)
        for row in attendee_reader:
            attendee = Attendee(**row)
            res[attendee.id] = attendee

    return res


def load_jobs(filename):
    res = {}
    with open(filename, newline='') as f:
        job_reader = csv.DictReader(f)
        for row in job_reader:
            job = Job(*row.values())
            res[job.id] = job

    return res


def load_shifts(filename, attendees, jobs):
    res = {}
    with open(filename, newline='') as f:
        job_reader = csv.DictReader(f)
        for row in job_reader:
            id, job_id, attendee_id, *rest = row.values()

            res[id] = Shift(id, jobs[job_id], attendees[attendee_id], *rest)

    return res

def dump_attendees(filename, attendees):
    with open(filename, 'w', newline='') as f:
        fields = ['id', 'first_name', 'last_name', 'email', 'can_spam', 'nonshift_hours', 'worked_hours',
                  'maybe_worked_hours', 'worked_other_event', 'review']
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for attendee in attendees:
            writer.writerow({
                'id': attendee.id,
                'first_name': attendee.first_name,
                'last_name': attendee.last_name,
                'email': attendee.email,
                'can_spam': attendee.can_spam,
                'nonshift_hours': attendee.nonshift_hours,
                'worked_hours': attendee.worked_hours(),
                'maybe_worked_hours': attendee.maybe_worked_hours(),
                'worked_other_event': attendee.worked_two_events(),
                'review': attendee.review()
            })


def main():
    if len(sys.argv) < 4:
        print("Usage: {} <attendees.csv> <jobs.csv> <shifts.csv> [eligible_output.csv] [review_output.csv]".format(sys.argv[0]))
        return

    attendees = load_attendees(sys.argv[1])
    jobs = load_jobs(sys.argv[2])
    shifts = load_shifts(sys.argv[3], attendees, jobs)

    output_filename = 'eligible.csv'
    if len(sys.argv) >= 5:
        output_filename = sys.argv[4]

    review_filename = 'need_review.csv'
    if len(sys.argv) >= 6:
        review_filename = sys.argv[5]

    for shift in shifts.values():
        if shift.worked:
            job = shift.job
            shift.attendee.shifts.append(shift)

    eligible = [a for a in attendees.values() if a.eligible()]
    review = [a for a in attendees.values() if a.review()]

    dump_attendees(output_filename, eligible)
    dump_attendees(review_filename, review)

    print('Found {} eligible staffers, with {} needing manual review'.format(len(eligible), len(review)))

if __name__ == "__main__":
    main()
