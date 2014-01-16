#!/usr/bin/env python
import storage
import os
import audiotools
import sys

def store_dir(d):
    store = storage.HashStore()
    for root, bar, files in os.walk(d):
        for filename in files:
            filename = root + '/' + filename
            try:
                #print "Storing", filename
                store.store_file(filename)
                print "Stored %s" % filename
            except audiotools.UnsupportedFile:
                print "Skipping unsupported file %s" % filename
            except Exception, e:
                print e, filename

def main():
    if len(sys.argv) > 1:
        d = sys.argv[1]
    else:
        d = raw_input("Enter the path to the music directory: ")
    store_dir(d)
    print "Done."

if __name__ == '__main__':
    main()
