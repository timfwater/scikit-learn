"""
Graph utilities and algorithms

Graphs are represented with their adjacency matrices, preferably using 
sparse matrices.
"""

# Authors: Aric Hagberg <hagberg@lanl.gov> 
#          Gael Varoquaux <gael.varoquaux@normalesup.org>
# License: BSD

import numpy as np
from scipy import sparse

################################################################################
# Path and connected component analysis.
# Code adapted from networkx

def single_source_shortest_path_length(graph, source, cutoff=None):
    """Return the shortest path length from source to all reachable nodes.

    Returns a dictionary of shortest path lengths keyed by target.

    Parameters
    ----------
    graph: sparse matrix or 2D array (preferably LIL matrix)
        Adjency matrix of the graph
    source : node label
       Starting node for path
    cutoff : integer, optional
        Depth to stop the search - only
        paths of length <= cutoff are returned.

    Examples
    --------
    >>> import numpy as np
    >>> graph = np.array([[ 0, 1, 0, 0],
    ...                   [ 1, 0, 1, 0],
    ...                   [ 0, 1, 0, 1],
    ...                   [ 0, 0, 1, 0]])
    >>> single_source_shortest_path_length(graph, 0)
    {0: 0, 1: 1, 2: 2, 3: 3}
    >>> single_source_shortest_path_length(np.ones((6, 6)), 2)
    {2: 0, 3: 1, 4: 1, 5: 1}
    """
    if sparse.isspmatrix(graph):
        graph = graph.tolil()
    else:
        graph = sparse.lil_matrix(graph)
    seen = {}                  # level (number of hops) when seen in BFS
    level = 0                  # the current level
    next_level = [source]    # dict of nodes to check at next level
    while next_level:
        this_level = next_level  # advance to next level
        next_level = set()       # and start a new list (fringe)
        for v in this_level:
            if v not in seen: 
                seen[v] = level # set the level of vertex v
                neighbors = np.array(graph.rows[v])
                # Restrict to the upper triangle
                neighbors = neighbors[neighbors > v]
                next_level.update(neighbors) 
        if cutoff is not None and cutoff <= level:
            break
        level += 1
    return seen  # return all path lengths as dictionary


def _cs_graph_components(graph):
    """ Return the connected components of a graph stored as an adjacency
        matrix. This is an equivalent of the
        scipy.sparse.cs_graph_components function introduced in scipy 0.9


        Parameters
        -----------
        x: ndarray-like, 2 dimensions, or sparse matrix
            The adjacency matrix of the graph. Only the upper triangular part
            is used.
        
        Returns
        --------
        n_comp: int
            The number of connected components.
        label: ndarray (ints, 1 dimension):
            The label array of each connected component (-2 is used to
            indicate empty rows: 0 everywhere, including diagonal).
        
        Notes
        ------
        
        The matrix is assumed to be symmetric and the upper triangular part
        of the matrix is used. The matrix is converted to a CSR matrix unless
        it is already a CSR.
        
        Example
        -------
        
        >>> import numpy as np
        >>> D = np.eye(4)
        >>> D[0,1] = D[1,0] = 1
        >>> _cs_graph_components(D)
        (3, array([0, 0, 1, 2]))
        >>> from scipy.sparse import dok_matrix 
        >>> _cs_graph_components(dok_matrix(D))
        (3, array([0, 0, 1, 2]))

    """
    if sparse.isspmatrix(graph):
        graph = graph.tolil()
    else:
        graph = sparse.lil_matrix(graph)
    seen = set()
    n_vertices = graph.shape[0]
    label  = -np.ones(n_vertices, dtype=np.int)
    n_comp = 0
    for v in np.where(graph.rows)[0]:
        if v not in seen:
            c = single_source_shortest_path_length(graph, v).keys()
            label[c] = n_comp
            seen.update(c)
            n_comp += 1
    return n_comp, label
    


if hasattr(sparse, 'cs_graph_components'):
    cs_graph_components = sparse.cs_graph_components
else:
    cs_graph_components = _cs_graph_components


################################################################################
# Graph laplacian
def _graph_laplacian_sparse(graph, normed=False, return_diag=False):
    n_nodes = graph.shape[0]
    if not graph.format == 'coo':
        lap = -graph.tocoo()
    else:
        lap = -graph.copy()
    diag_mask = (lap.row == lap.col)
    if not diag_mask.sum() == n_nodes:
        # The sparsity pattern of the matrix has holes on the diagonal,
        # we need to fix that
        diag_idx = lap.row[diag_mask]
        lap = lap.tolil()
        diagonal_holes = list(set(range(n_nodes)).difference(
                                diag_idx))
        lap[diagonal_holes, diagonal_holes] = 1
        lap = lap.tocoo()
        diag_mask = (lap.row == lap.col)
    lap.data[diag_mask] = 0
    w = -np.asarray(lap.sum(axis=1)).squeeze()
    if normed:
        w = np.sqrt(w)
        w_zeros = w == 0
        w[w_zeros] = 1
        lap.data /= w[lap.row]
        lap.data /= w[lap.col]
        lap.data[diag_mask] = 1-w_zeros
    else:
        lap.data[diag_mask] = w[lap.row[diag_mask]]
    if return_diag:
        return lap, w
    return lap


def _graph_laplacian_dense(graph, normed=False, return_diag=False):
    n_nodes = graph.shape[0]
    lap = -graph.copy()
    lap.flat[::n_nodes+1] = 0
    w = -lap.sum(axis=0)
    if normed:
        w = np.sqrt(w)
        w_zeros = w == 0
        w[w_zeros] = 1
        lap /= w
        lap /= w[:, np.newaxis]
        lap.flat[::n_nodes+1] = 1-w_zeros
    else:
        lap.flat[::n_nodes+1] = w
    if return_diag:
        return lap, w
    return lap
    

def graph_laplacian(graph, normed=False, return_diag=False):
    if normed and (np.issubdtype(graph.dtype, np.int)
                    or np.issubdtype(graph.dtype, np.uint)):
        graph = graph.astype(np.float)
    if sparse.isspmatrix(graph):
        return _graph_laplacian_sparse(graph, normed=normed,
                                       return_diag=return_diag)
    else:
        # We have a numpy array
        return _graph_laplacian_dense(graph, normed=normed,
                                       return_diag=return_diag)
 
