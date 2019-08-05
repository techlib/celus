import argparse
import csv
from io import StringIO
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rewrite CSV to ensure all fields are taken as '
                                                 'text')
    parser.add_argument('input_file', help='input CSV file with Sushi credentials')
    args = parser.parse_args()

    output = StringIO()
    counter = 0
    with open(args.input_file, 'r') as infile:
        reader = csv.reader(infile)
        writer = csv.writer(output, dialect='unix')
        for line in reader:
            writer.writerow(line)
            counter += 1
    with open(args.input_file, 'w') as outfile:
        outfile.write(output.getvalue())
    print('Processed {} lines'.format(counter), file=sys.stdout)
