#!/bin/bash

# Cascade trainer script
# ----------------------
# Purpose: This script can be used to download negative images from a file with URLs, generate positive images
# from these and a list of provided custom positives (data augmentation) and then train a cascade on the accumulated data.
# Dependencies: ImageMagick, opencv
#
# Must be provided before run: folder of original positive images
# Will be provided after run: folder of negative images, list of negatives, list of positives, folder of generated positive images
#
# Hints from various cascade training results in literature:
# - Ideally, the negative images will be similar to the positive but without the desired object in them, perhaps even with a similar
#   object to distinguish the desired object even more.
# - If a training stage only selects a few features (few rows/values of N), it is possible that the resulting matching will be poor
#   and the data for the classifer has to be improved.
# - A suggested positive to negative sample ratio is 2/1 even though opinions differ significantly.
# - The data augmentation part below is recommended only if you want to detect the same particular object - in case you want to detect
#   a category of this object (something a bit more genera) you might need to prepare the positives manually.
# - At least 1000 (positive or negative) samples are recommented for any training process.
#
# Note: This script assumes JPEG images throughout.

# directories and files listing postive and negative samples
origposdir="pos_orig"
genposdir="pos_gen"
negdir="neg"
poslist="pos.txt"
neglist="neg.txt"

# width and height of the provided positive images
poswidth=200
posheight=150
# url source: 0 for file, 1 for url, 2 for syncset
negsource=0
# parameter to use for the negative images
sourceparam="urls.txt"  # ="n00021939" for negsource=2, etc.
# maximal acceptable ratio of false positives (misclassified negatives) to negatives
max_false_alarm_rate=0.5
# minimal acceptable ratio of true positives to positives
min_hit_rate=0.995
# minimal number of training stages
number_of_stages=20
# the algorithm requires to use less than the available positives in training (exclude ~10%)
posexcluded=5
# times fewer negatives to train on w.r.t. positives (suggested: positive # = 2 * negative #)
postimes=2

# prepare negative images source
if [ $negsource = 0 ]
then
    urls_file=$sourceparam
    urls=$(cat "$urls_file" | dos2unix)
elif [ $negsource = 1 ]
then
    urls_addr=$sourceparam
    urls=$(curl "$urls_addr" | dos2unix)
elif [ $negsource = 2 ]
then
    rm -f urls.txt; touch urls.txt
    synset_id=$sourceparam
    synset_tree="http://image-net.org/api/text/wordnet.structure.hyponym?wnid=$synset_id"
    for synset in $(curl "$synset_tree" | dos2unix | sed s/-//)
    do
        chunk=$(curl "http://image-net.org/api/text/imagenet.synset.geturls?wnid=$synset")
        if [ "$chunk" != "The synset is not ready yet. Please stay tuned!" ]; then echo "$chunk" >> urls.txt; fi
    done
    urls=$(cat urls.txt | dos2unix)
fi

# download negative images from a URLs
rm -fr "$negdir"; mkdir "$negdir"
count=0
for url in $urls
do
    negimg="$(printf %04d $count).jpg"
    echo "Downloading image $url as $negimg"
    curl -# -m 60 "$url" > "$negimg"
    # negative image must be 2x the size of positives for the data augmenation part
    convert "$negimg" -resize $(($poswidth*2))x$(($posheight*2))! "$negimg"
    if [ $? != 0 ] || [ "$(wc -c "$negimg" | awk '{print $1}')" = 0 ]
    then
        echo "Removing $negimg due to error in downloading/converting"
        rm "$negimg"
    else
        mv "$negimg" "$negdir"/
        echo "Image $negimg obtained succesfully"
    fi
    count=$(($count+1))
done

# create file to list all negative images
find $negdir -iname "*.jpg" > $neglist
touch $poslist
# create directory to stich all samples together
mkdir $genposdir
postotal=$(ls "$origposdir" | wc -l)
negtotal=$(ls "$negdir" | wc -l)
samples=$(($negtotal/$postotal))

# produce samples for each original positive image
for img in $(ls $origposdir)
do
    # augment the available positive data
    echo "Creating samples for $img"
    opencv_createsamples -img "$origposdir/$img" -bg "$neglist" -info "_$poslist" -maxxangle 0.1 -maxyangle 0.1 -maxzangle 0.1 -maxidev 50 -num $samples

    echo "Adding samples for $img to the general sample folder and list"
    mincount=$(ls "$genposdir" | wc -l)
    for genimg in *.jpg
    do
        currcount=$(echo "$genimg" | sed 's/^\([0-9]\{4\}\).*/\1/')
        newimg=$(echo "$genimg" | sed "s/$currcount/$genposdir\/$(printf %04d $mincount)/")
        mv "$genimg" "$newimg"
        sed -i "s/$genimg/$(echo "$newimg" | sed -e 's/[\/&]/\\&/g')/" "_$poslist"
    done
    cat "_$poslist" >> "$poslist"
done

# create positive input vector
echo "Resizing and adding all samples to a vector to be used for training"
opencv_createsamples -info "$poslist" -num $negtotal -w $(($poswidth/2)) -h $(($posheight/2)) -vec positives.vec

# finally let's train
mkdir data
opencv_traincascade -data data -vec positives.vec -bg "$neglist" \
-numPos $(($negtotal-$posexcluded)) -numNeg $(($negtotal/$postimes)) -w $(($poswidth/2)) -h $(($posheight/2)) \
-numStages $number_of_stages -minHitRate $min_hit_rate -maxFalseAlarmRate $max_false_alarm_rate
