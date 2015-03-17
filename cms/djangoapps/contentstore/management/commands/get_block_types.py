"""
Script for finding courses with modules with multiple parents
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from xmodule.modulestore.django import modulestore
import csv
import datetime


class Command(BaseCommand):
    """List module counts in courses"""
    help = "List module counts in courses"

    def handle(self, *args, **options):
        "Execute the command"

        output_path = "module_counts.csv"
        if len(args) > 0:
            output_path = args[0]

        self.accepted_modules = None

        print "loading courses..."
        courses = modulestore().get_courses()
        print "courses loaded"
        header = ["course", "start date", "end date", "block_type", "count"]
        rows = [header]
        for index, course in enumerate(courses):
            print u"course {}, start: {}, end: {}".format(
                course.id, course.start, course.end
            )
            for block_type, count in self.walk_course_tree(course).iteritems():
                row = [course.id, course.start, course.end, block_type, count]
                rows.append(row)

                print u"\t{}: {}".format(block_type, count)
            print "\n"

        print "writing to {}...".format(output_path)
        with open(output_path, 'wb') as filehandle:
            writer = csv.writer(filehandle)
            writer.writerows(rows)

        print "success!"

    def walk_course_tree(self, course_descriptor, block_type_counts=None):
        if block_type_counts is None:
            block_type_counts = defaultdict(int)

        block_type = course_descriptor.scope_ids.block_type
        block_type_counts[block_type] += 1
        if hasattr(course_descriptor, 'children'):
            for child in course_descriptor.get_children():
                block_type_counts = self.walk_course_tree(child, block_type_counts)

        return block_type_counts
