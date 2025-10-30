import os
import sys
import argparse
from glob import glob

DATASET = ['training', 'test', 'validation']


def anno(of, gcs, path, cats, tg, mode='w'):
    if not cats:
        cats = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    
    o = open(of, mode) if of else sys.stdout
    for c in cats:
        x = os.path.join(path, c, '*.[jJ][pP][gG]')
        for f in glob(x):
            b = os.path.basename(f)
            blob = '/'.join([gcs, c, b])
            o.write(f'{tg}, {blob}, {c}\n')
    o.close()
                
parser = argparse.ArgumentParser()
parser.add_argument('categories', type=str, nargs='*',
                    help='categories to be annotated, default all')
parser.add_argument('-p', '--path', type=str, default='.',
                    help='path of data before categories, default .')
parser.add_argument('-b', '--bucket_path', type=str, required=True,
                    help='your bucket path in the format: gs://your_bucket/path/...')
parser.add_argument('-d', '--dataset', type=str, choices=DATASET, default=DATASET[0],
                    help='type of dataset, default training')
parser.add_argument('-a', '--append', action='store_true',
                    help='append mode if output to a file, default False')
parser.add_argument('-o', '--output', type=str,
                    help='file name for output; default stdout')
args = parser.parse_args()

mode = ['w', 'a'][args.append]
anno(of=args.output, gcs=args.bucket_path, path=args.path, cats=args.categories, tg=args.dataset, mode=mode)
