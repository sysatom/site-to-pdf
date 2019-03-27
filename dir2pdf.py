import os
import sys
from PyPDF2 import PdfFileReader, PdfFileMerger


class Dir2PDF():
    def __init__(self, dir_path, file_name):
        self.dir_path = dir_path
        self.file_name = file_name

    def run(self):
        merger = PdfFileMerger()
        for r, d, f in os.walk(self.dir_path):
            f.sort()
            for file in f:
                print('Appending ' + ('./%s/%s' % (self.dir_path, file)) + '...')
                fs = open('./%s/%s' % (self.dir_path, file), 'rb')
                merger.append(PdfFileReader(fs), import_bookmarks=False)

        merger.write(self.file_name)


if __name__ == '__main__':
    dir_arg = sys.argv[1]
    filename_arg = sys.argv[2]
    Dir2PDF(dir_arg, filename_arg).run()
