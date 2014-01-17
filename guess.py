import pyaudio
import threading

import storage
import identifier
import Queue
import time
import sys
from pprint import pprint

last_known_song = 'listening...'
def locate(user_string="$VER: Locate_Demo.py_Version_0.00.10_(C)2007-2012_B.Walker_G0LCU.", x=0, y=0):
    # Don't allow any user errors. Python's own error detection will check for
    # syntax and concatination, etc, etc, errors.
    x=int(x)
    y=int(y)
    if x>=255: x=255
    if y>=255: y=255
    if x<=0: x=0
    if y<=0: y=0
    HORIZ=str(x)
    VERT=str(y)
    # Plot the user_string at the starting at position HORIZ, VERT...
    print("\033["+VERT+";"+HORIZ+"f"+user_string)

class ProcessData(threading.Thread):
    def __init__(self, min_to_match=7):
        self.queue = Queue.Queue()
        self.output = None
        self.abandoned = False
        threading.Thread.__init__(self)
        self.daemon = True
        self.min_to_match = min_to_match

    def dump( self, chains_struct ):
        kl = chains_struct.keys()
        kl.sort()
        for x in xrange(50):
            print
        locate( user_string=last_known_song)
        for k in kl:
            try:
                chains = len( chains_struct[k] )
            except TypeError, just_an_int:
                chains = 0
            try:
                chunks = sum( [ x[-1] for x in chains_struct[k] ] )
            except TypeError, wha:
                chunks = 0
            try:
                max_chain = max( [ x[-1] for x in chains_struct[k] ] )
            except TypeError, gah:
                max_chain = 0;
            print max_chain, self.data.get_song(k).track_name, chains, chunks, [("%.2f"%x[1],x[-1]) for x in chains_struct[k] ]
        print


    def push_data(self, time, data):
        self.queue.put((time, data), False)

    def abandon(self):
        self.abandoned = True

    def run(self):
        global last_known_song
        self.data = storage.HashStore()


        # Dict of chunk_chains, given as {song_id: [song_id, last_offset, song_time, chain_length]}
        # Each entry represents a chain of matching points we've found from our incoming mic
        # data. The longer the chain, the more convincing the match.
        chunk_chains = {}
        longest_chain = 0
        best_guess = None
        while not self.abandoned or not self.queue.empty():
            self.dump( chunk_chains )
            if self.queue.qsize() > 20:
                print "Large backlog: %d" % self.queue.qsize()
            t, data = self.queue.get()

            c = identifier.AudioChunk.from_bytes(t, data)

            # Look up any chunks we have in storage by that hash.
            chunks = self.data.get_chunks(c.hash())
            if chunks is not None:

                # Iterate over each chunk we got that matches our hash.
                # For each of those chunks, compare against our 'chunk chains'.
                # If it's the same song and the time offset matches, update that
                # 'chain' with its new length and offset information.
                for new in chunks:
                    handled = False
                    for chain in chunk_chains.get(new.song_id, []):
                        #print chain
                        if abs((t - chain[1]) - (new.time - chain[2])) < 0.07:
                            chain[1] = t
                            chain[2] = new.time
                            chain[3] += 1
                            if chain[3] > longest_chain:
                                longest_chain = chain[3]
                                best_guess = chain[0]
                                last_known_song = 'prolly ' + self.data.get_song(best_guess).track_name
                                print "Current best (of %d partial matches): %d chain, %d - %s" % (len(chunk_chains), longest_chain, best_guess, self.data.get_song(chain[0]).track_name)

                            handled = True
                            break

                    # If we didn't manage to add this to a chain, create a new entry in the list.
                    if not handled:
                        chunk_chains.setdefault(new.song_id,[]).append([new.song_id, t, new.time, 1])
            
            time.sleep(0) # Make sure we aren't hogging the GIL and blocking the mic read.

            for chain_song in chunk_chains:
                for chain in chunk_chains[chain_song]:
                    # If we have a chain with over twenty matches, call it a win and bail out.
                    if chain[3] >= self.min_to_match:
                        print "song %d" % chain[0]
                        song = self.data.get_song(chain[0])
                        self.output = (song, chain[2])
                        last_known_song = song.track_name
                        return

def identify_from_mic(seconds_to_sample=30, min_to_match=7):
    p = pyaudio.PyAudio()
    # This is the same set of parameters we used (or, at least, assume) for decoding audio.
    # These must match for sane output.
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=4096)

    time = 0.0

    worker = ProcessData( min_to_match )
    worker.start()
    #print "sampling...", ;sys.stdout.flush()
    while time < seconds_to_sample:
        #print ".", ;sys.stdout.flush()
        data = stream.read(4096)
        worker.push_data(time, data)
        time += (4096/44100.0)

        if worker.output is not None:
            return worker.output

    # Wait for our worker to catch up if we've bailed out
    print
    worker.abandon()
    worker.join()
    if worker.output is not None:
        return worker.output

    return None, None
