#!/usr/bin/env python3
import sys
import csv
import json
from collections import Counter


class Person:
    def __init__(self, id, first_name, last_name, email, can_spam, nonshift_hours, worked_hours,
                 maybe_worked_hours, worked_other_event, review):
        self.id = id
        self.first_name = first_name.lower().title()
        self.last_name = last_name.lower().title()
        self.email = email.lower()
        self.can_spam = (can_spam == 'True')
        self.nonshift_hours = float(nonshift_hours)
        self.worked_hours = float(worked_hours)
        self.maybe_worked_hours = (maybe_worked_hours == 'True')
        self.worked_other_event = (worked_other_event == 'True')
        self.review = (review == 'True')

        self.others = []

    def merge(self, other):
        self.others.append(other)

    def __str__(self):
        return ','.join([str(v) for v in [self.id, self.first_name, self.last_name, self.email, self.can_spam, self.nonshift_hours,
                        self.worked_hours, self.maybe_worked_hours, self.worked_other_event, self.review]])

    def eligible(self):
        worked = 0
        for person in [self] + list(self.others):
            if person.worked_hours + person.nonshift_hours >= 18:
                worked += 1

        return worked >= 2 or (worked == 1 and self.worked_other_event)

    def full_name(self):
        return ' '.join((self.first_name, self.last_name))

    def __eq__(self, other):
        return (self.full_name() == other.full_name()
                and self.email == other.email)

    def __hash__(self):
        return hash((self.full_name(), self.email))


def load_people(filename):
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield Person(**row)


def check_field(val, person, map, sames):
    if val in map:
        for p in map[val]:
            if p == person:
                break
        else:
            map[val].append(person)

            if val in sames:
                sames[val].append(person)
            else:
                sames[val] = [person]
    else:
        map[val] = [person]



def main():
    if len(sys.argv) < 2:
        print("Usage: {} <eligible.csv> [<eligible2.csv>...]".format(sys.argv[0]))
        return

    deduped = {}
    by_name = {}
    by_email = {}
    by_lname = {}
    #by_birthday = {}

    same_names = {}
    same_emails = {}
    same_lnames = {}
    #same_birthdays = {}

    for f in sys.argv[1:]:
        for person in load_people(f):
            if person in deduped:
                deduped[person].merge(person)
            else:
                deduped[person] = person

            check_field(person.full_name(), person, by_name, same_names)
            check_field(person.email, person, by_email, same_emails)
            check_field(person.last_name, person, by_lname, same_lnames)
            #check_field(person.birthdate, person, by_birthday, same_birthdays)

    print("{} full name collisions".format(len(same_names)))
    print("{} email collisions".format(len(same_emails)))
    print("{} last name collisions".format(len(same_lnames)))
    #print("{} birthday collisions".format(len(same_birthdays)))

    assert sum((len(l) for l in by_name.values())) == sum((len(l) for l in by_email.values())) == sum((len(l) for l in by_lname.values()))

    eligible = 0
    ineligible = 0

    with open("final_eligible.csv", "w", newline='') as f:
        fields = ['id', 'first_name', 'last_name', 'email', 'can_spam', 'nonshift_hours', 'worked_hours',
                  'maybe_worked_hours', 'worked_other_event', 'review']
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for person in deduped.values():
            if person.eligible():
                eligible += 1
                writer.writerow({
                    'id': person.id,
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'email': person.email,
                    'can_spam': person.can_spam,
                    'nonshift_hours': person.nonshift_hours,
                    'worked_hours': person.worked_hours,
                    'maybe_worked_hours': person.maybe_worked_hours,
                    'worked_other_event': person.worked_other_event,
                    'review': person.review
                })
            else:
                ineligible += 1

    print("Eligible: {}\nIneligible: {}\nTotal: {}".format(eligible, ineligible, len(deduped)))

    print("Auto-merged staffers (same name and e-mail):")
    for p in deduped.values():
        if len(p.others):
            hours_str = ' + '.join((str(o.nonshift_hours + o.worked_hours) for o in [p]+p.others))
            print(" * {:20s} ({} staffers with {} hours)".format(p.full_name(), len(p.others)+1, hours_str))

    print()
    print("======================")
    print()

    for k, l in same_emails.items():
        if len(l) > 1:
            print("{} staffers with same email: {}".format(len(l), k))
            for person in l:
                print(" * {} {} (eligible: {})".format(person.first_name, person.last_name, person.eligible()))
            print()

    print()
    print("======================")
    print()

    for k, l in same_names.items():
        if len(l) > 1:
            print("{} staffers with same name: {}".format(len(l), k))
            for person in l:
                print(" * {} (eligible: {})".format(person.email, person.eligible()))
            print()


if __name__ == "__main__":
    main()
