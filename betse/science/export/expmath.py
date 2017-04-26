#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Utility functions of general-purpose relevance to all plots and animations.
'''

# ....................{ IMPORTS                            }....................
from betse.lib.numpy import arrays
from betse.util.type import ints, types
from betse.util.type.types import (
    type_check, NumericOrSequenceTypes, NumericTypes)

# ....................{ CONSTANTS                          }....................
UPSCALER_COORDINATES = ints.INVERSE_MICRO
'''
Multiplicative factor for upscaling cell cluster coordinates from micro-prefixed
units (i.e., `10**−6`) to unprefixed units, often to improve the readability of
these coordinates in user-friendly exports.
'''

# ....................{ UPSCALERS ~ cell : data            }....................
@type_check
def upscale_units_milli(
    cell_data: NumericOrSequenceTypes) -> NumericOrSequenceTypes:
    '''
    Upscale the contents of the number or sequence of numbers whose units are
    assumed to be denominated in a milli- prefix (i.e., ``10**-3``).

    This function does *not* modify the passed object. If this object is:

    * A scalar number (e.g., of type :class:`int` or :class:`float`), this
      function returns a new scalar number of the same type multiplied by a
      positive constant.
    * A Numpy array, this function returns a new Numpy array equal to the
      passed array multiplied by a positive constant.
    * A Python sequence (e.g., :class:`list`), this function returns a new Numpy
      array equal to the passed sequence converted into a new Numpy array and
      then multiplied by a positive constant.

    Parameters
    ----------
    cell_data : NumericOrSequenceTypes
        Either:
        * If this data is numeric, this number upscaled by this multiplier.
        * If this data is sequential, this sequence converted into a Numpy array
          whose elements are upscaled by this multiplier.

    Returns
    ----------
    object
        Upscaled object as described above.
    '''

    return _upscale_data_in_units(
        data=cell_data, factor=ints.INVERSE_MILLI)

# ....................{ UPSCALERS ~ cell : coordinates     }....................
@type_check
def upscale_coordinates(
    cell_coordinates: NumericOrSequenceTypes) -> NumericOrSequenceTypes:
    '''
    Upscale the contents of the passed number or sequence of numbers whose units
    are assumed to be denominated in micrometers (i.e., ``10**-6``), typically
    for converting spatial data into X and Y coordinates suitable for plot and
    animation display.

    Parameters
    ----------
    cell_coordinates : NumericOrSequenceTypes
        Number or sequence to be upscaled.

    Returns
    ----------
    NumericOrSequenceTypes
        Either:
        * If this data is numeric, this number upscaled by this multiplier.
        * If this data is sequential, this sequence converted into a Numpy array
          whose elements are upscaled by this multiplier.

    See Also
    ----------
    :func:`upscale_units_milli`
        Further details.
    '''

    return _upscale_data_in_units(
        data=cell_coordinates, factor=UPSCALER_COORDINATES)


@type_check
def upscale_coordinates_tuple(
    *cells_coordinates: NumericOrSequenceTypes) -> tuple:
    '''
    Upscale the contents of each passed number or sequence of numbers whose
    units are assumed to be denominated in micrometers (i.e., ``10**-6``),
    returning an n-tuple of each upscaled number or sequence of numbers.

    Parameters
    ----------
    cells_coordinates : tuple[NumericOrSequenceTypes]
        Tuple of all numbers and sequences to be upscaled.

    Returns
    ----------
    tuple
        N-tuple for ``N`` the number of passed positional arguments such that
        each element is the corresponding positional argument upscaled by the
        :func:`upscale_coordinates` function.
    '''

    return tuple(
        upscale_coordinates(cell_coordinates)
        for cell_coordinates in cells_coordinates
    )

# ....................{ UPSCALERS ~ private                }....................
@type_check
def _upscale_data_in_units(
    data: NumericOrSequenceTypes, factor: NumericTypes) -> (
    NumericOrSequenceTypes):
    '''
    Upscale the contents of the passed object by the passed multiplier,
    typically under the assumption that these contents are denominated in the
    reciprocal units of this multiplier (i.e., ``10**6`` for micrometers).

    Parameters
    ----------
    data : NumericOrSequenceTypes
        Number or sequence to be upscaled.
    factor : NumericTypes
        Reciprocal of the units this object is denominated in.

    Returns
    ----------
    NumericOrSequenceTypes
        Either:
        * If this data is numeric, this number upscaled by this multiplier.
        * If this data is sequential, this sequence converted into a Numpy array
          whose elements are upscaled by this multiplier.

    See Also
    ----------
    :func:`upscale_units_milli`
        Further details.
    '''

    # If the passed object is numeric, return this number upscaled.
    if types.is_numeric(data):
        return data * factor
    # Else, this object is a sequence. Return this sequence converted into a
    # Numpy array and then upscaled.
    else:
        return arrays.from_sequence(data) * factor
