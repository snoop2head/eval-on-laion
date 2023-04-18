import sys
import os
import argparse
import pickle
import json

import numpy as np
from tqdm import tqdm
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

import configs
from utils import logging_utils as logu
from utils.logging_utils import print_verbose
from utils import laion_utils as laionu


if __name__ == '__main__':
    # ----- Get arguments from input -----
    parser = argparse.ArgumentParser()

    # Path
    parser.add_argument('--clip_retrieval_json_path', type=str,
                        default=os.path.join('laion400m', 'processed', 'from_clip_retrieval',
                                             'top50_val_most_similars_from_laion_400m.json'))

    parser.add_argument('--image_labels_path', type=str,
                        default=os.path.join('ilsvrc2012', 'processed', 'imagename2wnid.pkl'))

    parser.add_argument('--laion_path', type=str, default=os.path.join('laion400m'))

    parser.add_argument('--labels_path', type=str, default=os.path.join('laion400m', 'processed', 'ilsvrc_labels'))

    # Sampling
    parser.add_argument('--do_sample', action='store_true')

    # Logging
    parser.add_argument('--no_verbose', dest='verbose', action='store_false')

    # Overwrite?
    parser.add_argument('--no_safe', dest='safe', action='store_false')

    # Convert to dictionary
    params = vars(parser.parse_args())

    # ----- Init. -----
    logu.verbose = params['verbose']

    open_type = 'xb' if params['safe'] else 'wb'

    # ----- Loading -----
    print_verbose('loading ...')

    print_verbose('\tloading clip retrieval results ...')
    with open(params['clip_retrieval_json_path'], 'r') as f:
        cr_results = json.load(f)
    cr_results = {int(k): v for k, v in cr_results.items()}

    print_verbose('\tloading image labels ...')
    with open(params['image_labels_path'], 'rb') as f:
        imagename2wnid = pickle.load(f)

    print_verbose('done!\n')

    # ----- Reformat -----
    wnid2crindices = {}
    wnid2crindex2sims = {}
    df_index = []
    df_dict = {
        configs.LAIONConfig.URL_COL: [],
        configs.LAIONConfig.TEXT_COL: []
    }
    cr_idx_lookup = {}

    for image_idx, results in tqdm(cr_results.items()):
        image_name = 'ILSVRC2012_val_%08d.JPEG' % image_idx
        wnid = imagename2wnid[image_name]

        if wnid not in wnid2crindices:
            wnid2crindices[wnid] = set()
        if wnid not in wnid2crindex2sims:
            wnid2crindex2sims[wnid] = {}

        for res in results:
            if params['do_sample'] and len(wnid2crindices[wnid]) >= configs.LAIONSamplingConfig.UNIFORM_SAMPLES:
                break

            cr_idx = res[configs.CLIPRetrievalConfig.ID_COL]
            similarity = res[configs.CLIPRetrievalConfig.SIMILARITY_COL]

            wnid2crindices[wnid].add(cr_idx)

            if cr_idx not in wnid2crindex2sims[wnid]:
                wnid2crindex2sims[wnid][cr_idx] = []
            wnid2crindex2sims[wnid][cr_idx].append(similarity)

            if cr_idx in cr_idx_lookup:
                continue
            else:
                cr_idx_lookup[cr_idx] = True

            df_index.append(cr_idx)

            df_dict[configs.LAIONConfig.URL_COL].append(res[configs.CLIPRetrievalConfig.URL_COL])
            df_dict[configs.LAIONConfig.TEXT_COL].append(res[configs.CLIPRetrievalConfig.TEXT_COL])

    # ----- Parse -----
    # Create a dataframe
    df = pd.DataFrame(df_dict, index=df_index)

    # Set to list
    wnid2crindices = {wnid: list(cr_indices) for wnid, cr_indices in wnid2crindices.items()}

    # Average similarities
    wnid2crimgimgsims = {}
    for wnid, cr_indices in wnid2crindices.items():
        similarities = [np.mean(wnid2crindex2sims[wnid][cr_idx]) for cr_idx in cr_indices]
        wnid2crimgimgsims[wnid] = similarities

    # ----- Save -----
    print_verbose('saving...')

    # Save labels
    print_verbose(f'\tsaving distinct {len(wnid2crindices)} labels.')

    with open(os.path.join(params['labels_path'], 'wnid2crindices.pkl'), open_type) as f:
        pickle.dump(wnid2crindices, f)

    # Save similarities
    print_verbose(f'\tsaving image to text similarities.')

    with open(os.path.join(params['labels_path'], 'wnid2crimgimgsims.pkl'), open_type) as f:
        pickle.dump(wnid2crimgimgsims, f)

    # Save df
    print_verbose(f'\tsaving df with {len(df)} rows.')

    prefix = configs.LAIONConfig.SUBSET_CLIP_RETRIEVAL_PREFIX
    # For compatibility only
    subset_file_name = prefix + laionu.get_laion_subset_file_name(0, configs.LAIONConfig.NUM_PARTS - 1)
    subset_file_path = os.path.join(params['laion_path'], subset_file_name)

    if os.path.exists(subset_file_path) and params['safe']:
        raise Exception('Subset already exists!')

    df.to_parquet(subset_file_path, index=True)

    print_verbose('done!\n')
