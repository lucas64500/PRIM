import numpy as np
import argparse
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score
import matplotlib.pyplot as plt
from sklearn.preprocessing import normalize
from copkmeans.cop_kmeans import cop_kmeans
import time


import operator




run_common_frames = True

def run(input_file, output_file, max_common_frames, n_clusters):
    input = np.load(input_file)


    #print(np.linalg.norm(input[0, 10:]))


    #Frame_id, track id, ., ., ., ., ., ., ., ., appearance features

    t_ = time.time()


    print("Input shape:", input.shape)
    ids = list(np.unique(input[:,1]))

    print(time.time() - t_)
    t_ = time.time()

    print("Total number of ids:",len(ids))
    ids_by_frames = {}
    for row in input:
        if row[0] not in ids_by_frames.keys():
            ids_by_frames[row[0]] = []
        ids_by_frames[row[0]].append(row[1])
    n_ids_by_frames = {k: len(v) for k, v in ids_by_frames.items()}
    plt.bar(n_ids_by_frames.keys(), n_ids_by_frames.values(), color='g')
    #plt.show()


    print("Maximum number of ids on the same frame:", max(n_ids_by_frames.values()))
    ff = []
    for f, nid in n_ids_by_frames.items():
        if nid > n_clusters:
            ff.append(f)
    print("Delete frames with n_detections > n_clusters:",len(ff),ff)
    input = np.array([x for x in input if x[0] not in ff])
    min_len_tracklet = 10
    print("Delete tracklets with n_detections < ",min_len_tracklet)
    lens = []
    to_remove=[]
    for i in ids:
        t = input[input[:, 1] == i][:, 0]
        if t.shape[0] < min_len_tracklet:
            to_remove.append(i)
        else:
            lens.append(t.shape[0])
    for i in to_remove:
        ids.remove(i)
        input = input[~(input[:, 1] == i)]
    print(input.shape,"detections x features")
    print("Mean len of tracklets (in frames):", np.mean(lens))


    random_data = []
    data = []
    for i in ids:
        group = input[:, 1] == i
        n_frames = input[group].shape[0]
        d = np.zeros(input[0,10:].shape[0]+2)
        d[0] = input[group][:, 0].min(axis=0)
        d[1] = i
        d[2:] = input[group][:, 10:].mean(axis=0)
        d[2:] = d[2:] / np.linalg.norm(d[2:]) * n_frames
        data.append(d)

        x = np.random.random(128)
        x = x / np.linalg.norm(x)
        random_data.append(list(d[:2]) + list(x))

    data = np.array(data)
    data = data[data[:, 0].argsort()]
    ids = list(data[:,1])

    random_data = np.array(random_data)

    common_frames = np.zeros((len(ids),len(ids)))
    if run_common_frames:
        print("Computing common frames matrix...")
        for i in range(len(ids)):
            for j in range(i, len(ids)):
                n_common_frames = len(set(list(input[input[:, 1] == ids[i]][:, 0])).intersection(list(input[input[:, 1] == ids[j]][:, 0])))
                common_frames[i,j] = n_common_frames
        print("Saved common frames matrix")
        np.save("common_frames.npy", common_frames)
    else:
        print("Loaded common frames matrix")
        common_frames = np.load("common_frames.npy")
    #print(common_frames, common_frames.shape)

    print("Computing 'cannot link' constraints with max_common_frames = ",max_common_frames)
    must_link = []
    cannot_link = [(i,j) for i in range(len(ids)) for j in range(i+1, len(ids)) if common_frames[i,j] > max_common_frames]
    #print(cannot_link)
    print("Number of constraints", len(cannot_link))


    #Initialisation des centroides
    ids_by_frames = {}
    for row in input:
        if row[0] not in ids_by_frames.keys():
            ids_by_frames[row[0]] = []
        ids_by_frames[row[0]].append(row[1])
    n_ids_by_frames = {k: len(v) for k, v in ids_by_frames.items()}
    ref_frame = max(n_ids_by_frames, key=lambda key: n_ids_by_frames[key])
    centers_ids_init=ids_by_frames[ref_frame]
    centers_init = [list(data[:,1]).index(i) for i in centers_ids_init]

    ids = list(np.unique(data[:, 1]))
    if (len(ids) < n_clusters):
        n_clusters = len(ids)
    clusters, centers = cop_kmeans(dataset=data[:,2:], initialization=centers_init,  k=n_clusters, ml=must_link, cl=cannot_link, spherical=True)


    #We then compute a clustering with random unit features and only the constraints (to compare)
    #random_clusters, random_centers = cop_kmeans(dataset=random_data, k=n_clusters, ml=must_link, cl=cannot_link, spherical=True)

    #print("Adjusted Rand Index between constrained k-means clustering and a constrained but random clustering", adjusted_rand_score(clusters, random_clusters))


    out_clusters = clusters

    output = input[:,:10]
    output[:,1] = np.array([out_clusters[ids.index(int(x))] for x in input[:,1]])
    #print("Output:", output)
    print("Output saved to:", output_file)
    np.save(output_file, output)


def parse_args():
    """ Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Post clustering")
    parser.add_argument(
        "--input_file", help="Tracking output in MOTChallenge file format.",
        default=None, required=True)
    parser.add_argument(
        "--output_file", help="Tracking output in MOTChallenge file format.",
        default=None, required=True)
    parser.add_argument(
        "--n_clusters", help="Number of clusters",
        default=None, required=True)
    parser.add_argument(
        "--max_common_frames", help="Maximum number of common frames (constraint)",
        default=0)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.input_file, args.output_file, int(args.max_common_frames), int(args.n_clusters))
