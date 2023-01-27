"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""
import os

import zarr
from datatree import open_datatree
from natsort import natsorted


def napari_get_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    # if we know we cannot read the file, we immediately return None.
    if isinstance(path, list):
        return None

    if not (path.endswith(".zarr") or path.endswith(".zarr" + os.sep)):
        return None

    root = zarr.open(path)
    if "multiscaleSpatialImageVersion" not in root.attrs:
        return None

    # otherwise we return the *function* that can read ``path``.
    return reader_function


def reader_function(path):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """
    multiscale = open_datatree(path, engine="zarr")
    scales = [
        childname
        for childname in multiscale.children
        if childname.startswith("scale")
    ]
    scales = natsorted(scales)

    multiscale_data = []
    for scale in scales:
        keys = multiscale[scale].data_vars.keys()
        assert len(keys) == 1
        dataset_name = [key for key in keys][0]
        dataset = multiscale[scale].data_vars.get(dataset_name)
        multiscale_data.append(dataset)

    # optional kwargs for the corresponding viewer.add_* method
    add_kwargs = {}

    # Find the scale and translation information for the highest res dataset
    scale = scales[
        0
    ]  # sorted list, first element corresponds to highest resolution dataset
    datasets = multiscale.attrs["multiscales"][0]["datasets"]
    for dataset in datasets:
        if scale in dataset["path"]:
            for coord_transform in dataset["coordinateTransformations"]:
                if "scale" in coord_transform:
                    add_kwargs["scale"] = coord_transform["scale"]
                if "translation" in coord_transform:
                    add_kwargs["translate"] = coord_transform["translation"]

    layer_type = "image"  # optional, default is "image"
    return [(multiscale_data, add_kwargs, layer_type)]
