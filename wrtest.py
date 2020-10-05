import time
import os
import speedtest
import sys
from statistics import mean, stdev
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import copy

# TODO:
# on Python 3.7.3: DeprecationWarning: time.clock has been deprecated in Python 3.3 and will be removed from Python 3.8: use time.perf_counter or time.process_time instead
# stress test many small files
# improve time measurement
  # check perf_counter() on unix-like systems
  # include python version check for perf_counter()
# check for any read/write failures and catch exceptions
  # lost connection
  # quota exceeded
  # bit errors, etc


# "repeats": number of times a file of certain size is written/read
#   "repeats" list may be shorter than "labels" or "sizes"
#   each file size must repeat at least 2 times
# repeats   = [100,    100,   50,      20,    15,     10,      4]
repeats   = [100,    100,   50,      10,    10,     4]
labels    = ["1KB", "10KB", "100KB", "1MB", "10MB", "100MB", "1GB"]  # used as labels in filenames and graph
sizes     = [i*j for i in [1024, 1024**2] for j in [1, 10, 100]] + [1024**3]  # actual file sizes as bytes
line_size = 1024**2*50  # files written in "line_size" chunks

#
# Test by writing or reading ("operation") test files (number specified by "repeats") of size (specified by "sizes")
# Read operation depends on prior execustion of Write operation
#
def run_test(avg_list, std_list, operation):
    for j in range(len(repeats)): # loop over block sizes
        filesize = sizes[j]
        timings = []
        for i in range(repeats[j]): # repeat timing
            filename = "testSize{}rep{}.txt".format(labels[j], i)
            print("{} test {}".format(operation, filename))
            t0=time.perf_counter()
            if operation == "write":
                f = open(filename, "w")
                num_lines = int(filesize/line_size)
                for _ in range(num_lines):
                    f.write("a"*line_size)
                f.write("a"*int(filesize%line_size))
                #print("num lines {} and remainder {}".format(num_lines, int(filesize%line_size)))
            else:
                with open(filename, "r") as fp:
                    a = fp.readline()
                # a = open(filename, "r").read() # TODO: read by line, add verification of string
            delta = time.perf_counter()-t0
            if delta == 0:  # some time counters like time.time() may return 0: break off experiment 
                timings.append(-1)
                print("break")
                break
            else:
                timings.append(filesize/1024**2/delta)  # convert to MB/s
        if -1 in timings:
            avg_list.append(0)
            std_list.append(0)
        else:
            avg_list.append(mean(timings))
            std_list.append(stdev(timings))
    print("avg results of {} test: {}".format(operation, avg_list))
    print("std results of {} test: {}".format(operation, std_list))


#
# run tests
# 
write_exps_avg = []
write_exps_std = []
read_exps_avg = []
read_exps_std = []

run_test(write_exps_avg, write_exps_std, "write")
run_test(read_exps_avg, read_exps_std, "read")


#
# parameter processing
#
def quick_remove(list, elem):
    try:
        list.remove(elem)
    except ValueError:
        pass

all_args = copy.deepcopy(sys.argv)
quick_remove(all_args, "noshow")
quick_remove(all_args, "nosave")
quick_remove(all_args, "networktest")
for arg in all_args:
    if arg.endswith(".py"):
        all_args.remove(arg)
title = "wrtest.py performance measurement"
if len(all_args) == 1:
    title = all_args[0]
elif len(all_args) > 1:
    print("Your output will be labeled {}", title)
    print("There should only be 1 param in: \"{}\": wrong or superfluous arguments?", all_args)


#
# plot results
# 
x = np.arange(len(repeats))  # the label locations
width = 0.45  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(x - width/2, read_exps_avg, width, yerr=read_exps_std, label='Read')
rects2 = ax.bar(x + width/2, write_exps_avg, width, yerr=write_exps_std, label='Write')

_, ymax = ax.get_ylim()
aSmidge = ymax/100 # small offset used to optimize position annotations

ax.set_ylabel('Avg speed (MB/s)')
ax.set_title(title)
ax.set_xticks(x)
ax.set_xticklabels(labels[:len(repeats)])
ax.legend()

# Annotations below (avg speed) and in or above the bar (number of repeats)
def autolabel(rects):
    for rect, i in zip(rects, range(len(rects))):
        height = rect.get_height()
        note_text = ""
        if height == 0:
            note_text = "err"
        else:
            if height < 10:
                note_text = '{:2.1f}'.format(height)
            else:
                note_text = '{:.0f}'.format(height)
        # Annotation below the bar for avg speed
        ax.annotate(note_text,
                    xy=(rect.get_x() + rect.get_width() / 2, 0),
                    xytext=(0, -12),
                    textcoords="offset points",
                    ha='center', va='bottom')
        if height/ymax < 0.1:
            repeat_Y_position = height + aSmidge
        else:
            repeat_Y_position = aSmidge
        # print("print at height {:.1f} for height {:.1f} with ymax {:.1f}".format(repeat_Y_position, height, ymax))
        # Annotation up or inside the left side of the bar indicating number of repetitions for experiment
        ax.annotate("x{}".format(repeats[i]),
                    xy=(rect.get_x() + rect.get_width() / 4, repeat_Y_position),
                    xytext=(0, aSmidge),
                    textcoords="offset points",
                    ha='center', va='bottom', rotation=90)

# apply annotations
autolabel(rects1)
autolabel(rects2)

# move x-tick labels down to make space for autolabels
dx = 0/72.; dy = -6/72. 
offset = matplotlib.transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
for label in ax.xaxis.get_majorticklabels():
    label.set_transform(label.get_transform() + offset)

# show network speed test up/download speeds
if "networktest" in sys.argv:
    print("Running network speed (option \"networktest\")")
    st = speedtest.Speedtest()
    st_down, st_up = st.download()/1024**2/8, st.upload()/1024**2/8
    print("down MB/s: {:.2f}".format(st_down))
    print("up   MB/s: {:.2f}".format(st_up))
    x_start, x_end = ax.get_xlim()
    plt.hlines([st_down, st_up], x_start, x_end, linestyles='dotted')
    plt.text(x_start,st_down+aSmidge,"down")
    plt.text(x_end,st_up+aSmidge, "up", horizontalalignment="right")
else:
    print("Not performing network speed test (option \"networktest\")")

if "nosave" not in sys.argv:
    print("Storing output in \"{}.png\" (any non-predefined parameter will be used as file name)".format(title))
    plt.savefig(title + ".png")

if "noshow" not in sys.argv:
    plt.show()
else:
    print("Not showing matplotlib interface (option \"noshow\")")

