#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

from betse.science.cells import Cells
from betse.science.parameters import Parameters
from betse.science.sim import Simulator
from betse.science.simrunner import SimRunner
from betse.util.type import types
from betse.util.type.types import type_check

from betse.science.filehandling import loadWorld, loadSim

@type_check
def seed(source : (SimRunner, str)) -> SimRunner:
    '''
    Seed a simulation returning a `SimRunner` instance.

    If *source* is an instance of `SimRunner`, then it is used to seed the
    world. Otherwise *source* is expected to be a path to a YAML configuration
    file, and is used to initialize a `SimRunner` which is then used to seed.

    Parameters
    ----------
    source
        Either an instance of `SimRunner` or the path to a YAML configuration
        file

    Returns
    -------
    An instance of `SimRunner`
    '''
    if types.is_simrunner(source):
        source.makeWorld()
        return source
    else:
        runner = SimRunner(config_filename=source)
        return seed(runner)

@type_check
def initialize(source : (SimRunner, str)) -> SimRunner:
    '''
    Run an initialization simulation returning a `SimRunner` instance.

    If *source* is an instance of `SimRunner`, then it is used run the
    initialization. Otherwise *source* is expected to be a path to a
    YAML configuration file, and is used to initialize a `SimRunner`
    which is then used to run the simulation.

    Parameters
    ----------
    source
        Either an instance of `SimRunner` or the path to a YAML configuration
        file

    Returns
    -------
    An instance of `SimRunner`
    '''
    if types.is_simrunner(source):
        source.initialize()
        return source
    else:
        runner = SimRunner(source)
        return initialize(runner)

@type_check
def simulate(source : (SimRunner, str)) -> SimRunner:
    '''
    Run a simulation returning a `SimRunner` instance.

    If *source* is an instance of `SimRunner`, then it is used run the
    simulation. Otherwise *source* is expected to be a path to a YAML
    configuration file, and is to initialize a `SimRunner` which is then used
    to run the simulation.

    Parameters
    ----------
    source
        Either an instance of `SimRunner` or the path to a YAML configuration
        file

    Returns
    -------
    An instance of `SimRunner`
    '''
    if types.is_simrunner(source):
        source.simulate()
        return source
    else:
        runner = SimRunner(source)
        return simulate(runner)

@type_check
def read_config(config_filename : str) -> Parameters:
    '''
    Read a configuration file into a `Parameters` object.

    Parameters
    ----------
    config_filename : str
        The filename of the YAML configuration file

    Returns
    -------
    A `Parameters` instance
    '''
    return Parameters(config_filename)

@type_check
def load_world(source : (Cells, Parameters, str)) -> tuple:
    '''
    Load a world from some *source*.

    Parameters
    ----------
    source
        An instance of `Cells` or `Parameters`, or a path to a YAML
        configuration file

    Returns
    -------
    (Cells, Parameters)
        A 2-tuple `(cells, p)` as loaded from the *source*
    '''
    if types.is_cells(source):
        return loadWorld(source.savedWorld)
    elif types.is_parameters(source):
        return load_world(Cells(source))
    else:
        return load_world(Parameters(source))

@type_check
def load_init(source : (Simulator, Parameters, str)) -> tuple:
    '''
    Load an initialization simulation from some *source*.

    Parameters
    ----------
    source
        An instance of `Simulator` or `Parameters`, or a path to a YAML
        configuration file

    Returns
    -------
    (Simulator, Cells, Parameters)
        A 3-tuple `(sim, cells, p)` as loaded from the *source*
    '''
    if types.is_simulator(source):
        return loadSim(source.savedInit)
    elif types.is_parameters(source):
        return load_init(Simulator(source))
    else:
        return load_init(Parameters(source))

@type_check
def load_sim(source : (Simulator, Parameters, str)) -> tuple:
    '''
    Load a simulation from some *source*.

    Parameters
    ----------
    source
        An instance of `Simulator` or `Parameters`, or a path to a YAML
        configuration file

    Returns
    -------
    (Simulator, Cells, Parameters)
        A 3-tuple `(sim, cells, p)` as loaded from the *source*
    '''
    if types.is_simulator(source):
        return loadSim(source.savedSim)
    elif types.is_parameters(source):
        return load_sim(Simulator(source))
    else:
        return load_sim(Parameters(source))