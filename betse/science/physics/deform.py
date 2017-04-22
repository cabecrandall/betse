
#!/usr/bin/env python3
# Copyright 2014-2017 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

import numpy as np
from betse.science import sim_toolbox as stb
from betse.util.io.log import logs
from scipy.interpolate import SmoothBivariateSpline

def getDeformation(sim, cells, t, p):
    """
    Calculate the deformation of the cell cluster under the action of
    intracellular forces and pressures, assuming steady-state (slow) changes.

    The method assumes that material is incompressible and total volume is
    conserved.

    The "galvanotropism" mechanism assumes growing and that ends of microtubules
    exert a cell-deforming force. Microtubules are in turn influenced by the
    electric field.

    If studying hydrostatic pressure deformations under osmotic influx, first,
    the equation of linear elastic motion is used to calculate deformation
    assuming full compressibility.

    The divergence of the resulting deformation field is calculated. An internal
    reaction pressure is calculated from the divergence. The gradient of the
    reaction pressure is subtracted from the initial solution to create a
    divergence-free (volume conserved) deformation field.
    """

    # Determine action forces
    #---------------------------------------------------------------------------------

    # calculate the gradient of any applied pressures:
    gPP = (sim.P_cells[cells.cell_nn_i[:, 1]] - sim.P_cells[cells.cell_nn_i[:, 0]]) / (cells.nn_len)

    gPx = -gPP*cells.nn_tx
    gPy = -gPP*cells.nn_ty

    sim.gPxc = np.dot(cells.M_sum_mems, gPx) / cells.num_mems
    sim.gPyc = np.dot(cells.M_sum_mems, gPy) / cells.num_mems

    mtx, mty = sim.mtubes.mtubes_to_cell(cells, p)

    # deformation by "galvanotropic" mechanism (electrostrictive forces
    # influenced by biology, e.g. cytoskeletal).
    Fx = (1 / p.lame_mu) * (mtx * p.galvanotropism + sim.gPxc)
    Fy = (1 / p.lame_mu) * (mty * p.galvanotropism + sim.gPyc)

    # Calculate flow under body forces using time-independent linear elasticity
    # equation.
    dxo = np.dot(cells.lapGJinv, -Fx)
    dyo = np.dot(cells.lapGJinv, -Fy)

    # Deformation must be made divergence-free. To do so, use the
    # Helmholtz-Hodge decomposition method.
    _, sim.d_cells_x, sim.d_cells_y, _, _, _ = cells.HH_cells(
        dxo, dyo, rot_only=True, bounds_closed=p.fixed_cluster_bound)

    if p.deform_osmo:
        # Calculate the pressure gradient resulting from finite-divergence
        # osmotic-pressure induced water flows to cells.
        gPP = (sim.PP[cells.cell_nn_i[:, 1]] - sim.PP[cells.cell_nn_i[:, 0]]) / (cells.nn_len)

        dx = -gPP * cells.nn_tx
        dy = -gPP * cells.nn_ty

        dxco = np.dot(cells.M_sum_mems, dx) / cells.num_mems
        dyco = np.dot(cells.M_sum_mems, dy) / cells.num_mems

        # _, dxc, dyc, _, _, _ = cells.HH_cells(dxco, dyco, rot_only=True,
        #                                                           bounds_closed=p.fixed_cluster_bound)

        sim.d_cells_x = sim.d_cells_x + dxco
        sim.d_cells_y = sim.d_cells_y + dyco


def timeDeform(sim, cells, t, p):
    """
    Calculates the deformation of the cell cluster under the action
    of intracellular pressure, considering the full time-dependent
    linear elasticity equation for an incompressible medium.

    The solution method for this equation is similar to the
    steady-state method of deformation(). First the displacement
    field is calculated assuming compressibility,
    a reaction pressure is calculated from the divergence of the
    initial field, and the gradient of the internal pressure is
    subtracted from the initial field to produce a divergence
    free solution.

    This method is working much better than the timeDeform_o()
    so is presently in active use.

    """

    # # Check for the adequacy of the time step:
    # step_check = (p.dt / (2 * p.rc)) * np.sqrt(p.lame_mu / 1000)
    #
    # if step_check > 1.0:
    #     new_ts = (0.9 * 2 * p.rc) / (np.sqrt(p.lame_mu / 1000))
    #
    #     raise BetseSimException(
    #         'Time dependent deformation is tricky business, requiring a small time step! '
    #         'The time step you are using is too large to bother going further with. '
    #         'Please set your time step to ' + str(new_ts) + ' and try again.')
    #
    k_const = (p.dt ** 2) * (p.lame_mu / 1000)

    # # Determine action forces ------------------------------------------------

    # pressures:
    if p.deform_osmo is True:

        Pcell = sim.P_cells +  sim.PP

    else:

        Pcell = sim.P_cells

    # calculate the gradient of any applied pressures:
    gPP = (Pcell[cells.cell_nn_i[:, 1]] - Pcell[cells.cell_nn_i[:, 0]]) / (cells.nn_len)

    gPx = -gPP * cells.nn_tx
    gPy = -gPP * cells.nn_ty

    sim.gPxc = np.dot(cells.M_sum_mems, gPx) / cells.num_mems
    sim.gPyc = np.dot(cells.M_sum_mems, gPy) / cells.num_mems

    # deformation by "galvanotropic" mechanism (electrostrictive forces influenced by biology, e.g. cytoskeletal):
    F_cell_x = (1 / p.lame_mu) * ( (1/sim.sigma) * sim.J_cell_x * sim.rho_cells * p.galvanotropism + sim.gPxc)
    F_cell_y = (1 / p.lame_mu) * ( (1/sim.sigma) * sim.J_cell_y * sim.rho_cells * p.galvanotropism + sim.gPyc)

    # -------------------------------------------------------------------------------------------------

    sim.dx_time.append(np.copy(sim.d_cells_x))  # append the solution to the time-save vector
    sim.dy_time.append(np.copy(sim.d_cells_y))

    # Initial value solution--------------------------------------------------------------------------------
    if t == 0.0:

        wave_speed = np.sqrt(p.lame_mu / 1000)
        wave_speed = np.float(wave_speed)
        wave_speed = np.round(wave_speed, 2)

        logs.log_info(
            'Your wave speed is approximately: ' +
            str(wave_speed) + ' m/s '
        )

        logs.log_info('Try a world size of at least: ' + str(round((5 / 3) * (wave_speed / 500) * 1e6))
                      + ' um for resonance.')

        if p.fixed_cluster_bound is True:

            sim.d_cells_x = k_const * np.dot(cells.lapGJ, sim.dx_time[-1]) + (k_const / p.lame_mu) * F_cell_x + \
                            sim.dx_time[-1]
            sim.d_cells_y = k_const * np.dot(cells.lapGJ, sim.dy_time[-1]) + (k_const / p.lame_mu) * F_cell_y + \
                            sim.dy_time[-1]

        else:

            sim.d_cells_x = k_const * np.dot(cells.lapGJ_P, sim.dx_time[-1]) + (k_const / p.lame_mu) * F_cell_x + \
                            sim.dx_time[-1]
            sim.d_cells_y = k_const * np.dot(cells.lapGJ_P, sim.dy_time[-1]) + (k_const / p.lame_mu) * F_cell_y + \
                            sim.dy_time[-1]


    elif t > 0.0:

        # do the non-initial value, standard solution iteration:

        # calculate the velocity for viscous damping:
        d_ux_dt = (sim.dx_time[-1] - sim.dx_time[-2]) / (p.dt)
        d_uy_dt = (sim.dy_time[-1] - sim.dy_time[-2]) / (p.dt)

        gamma = ((p.dt ** 2) * (p.mu_tissue * p.lame_mu)) / (1000 * (2 * p.rc))

        if p.fixed_cluster_bound is True:

            sim.d_cells_x = k_const * np.dot(cells.lapGJ, sim.dx_time[-1]) - gamma * d_ux_dt + \
                             (k_const / p.lame_mu) * F_cell_x + 2 * sim.dx_time[-1] - sim.dx_time[-2]

            sim.d_cells_y = k_const * np.dot(cells.lapGJ, sim.dy_time[-1]) - gamma * d_uy_dt + \
                             (k_const / p.lame_mu) * F_cell_y + 2 * sim.dy_time[-1] - sim.dy_time[-2]

        else:

            sim.d_cells_x = k_const * np.dot(cells.lapGJ_P, sim.dx_time[-1]) - gamma * d_ux_dt + \
                             (k_const / p.lame_mu) * F_cell_x + 2 * sim.dx_time[-1] - sim.dx_time[-2]

            sim.d_cells_y = k_const * np.dot(cells.lapGJ_P, sim.dy_time[-1]) - gamma * d_uy_dt + \
                             (k_const / p.lame_mu) * F_cell_y + 2 * sim.dy_time[-1] - sim.dy_time[-2]


    # Flow must be made divergence-free: use the Helmholtz-Hodge decomposition method:
    _, sim.d_cells_x, sim.d_cells_y, _, _, _ = cells.HH_cells(sim.d_cells_x, sim.d_cells_y, rot_only=True,
                                                              bounds_closed=p.fixed_cluster_bound)

    print(sim.d_cells_x.mean())


    # calculate divergence of u  -----------------------------------------------------------------------
    # FIXME this might be a great place for HH decomposition

    # # first interpolate displacement field at membrane midpoints:
    # ux_mem = interp.griddata((cells.cell_centres[:, 0], cells.cell_centres[:, 1]), sim.d_cells_x,
    #     (cells.mem_mids_flat[:, 0], cells.mem_mids_flat[:, 1]), fill_value=0)
    #
    # uy_mem = interp.griddata((cells.cell_centres[:, 0], cells.cell_centres[:, 1]), sim.d_cells_y,
    #     (cells.mem_mids_flat[:, 0], cells.mem_mids_flat[:, 1]), fill_value=0)
    #
    # # get the component of the displacement field normal to the membranes:
    # u_n = ux_mem * cells.mem_vects_flat[:, 2] + uy_mem * cells.mem_vects_flat[:, 3]
    #
    # # calculate divergence as the sum of this vector x each surface area, divided by cell volume:
    # div_u = (np.dot(cells.M_sum_mems, u_n * cells.mem_sa) / cells.cell_vol)
    #
    # if p.fixed_cluster_bound is True:
    #
    #     # calculate the reaction pressure required to counter-balance the flow field:
    #     P_react = np.dot(cells.lapGJ_P_inv, div_u)
    #
    # else:
    #
    #     # calculate the reaction pressure required to counter-balance the flow field:
    #     P_react = np.dot(cells.lapGJinv, div_u)
    #
    # # calculate its gradient:
    # gradP_react = (P_react[cells.cell_nn_i[:, 1]] - P_react[cells.cell_nn_i[:, 0]]) / (cells.nn_len)
    #
    # gP_x = gradP_react * cells.mem_vects_flat[:,2]
    # gP_y = gradP_react * cells.mem_vects_flat[:,3]
    #
    # # average the components of the reaction force field at cell centres and get boundary values:
    # gPx_cell = np.dot(cells.M_sum_mems, gP_x) / cells.num_mems
    # gPy_cell = np.dot(cells.M_sum_mems, gP_y) / cells.num_mems
    #
    # # calculate the displacement of cell centres under the applied force under incompressible conditions:
    # sim.d_cells_x = sim.d_cells_x - gPx_cell
    # sim.d_cells_y = sim.d_cells_y - gPy_cell


    # if p.fixed_cluster_bound is True:  # enforce zero displacement boundary condition:
    #
    #     sim.d_cells_x[cells.bflags_cells] = 0
    #     sim.d_cells_y[cells.bflags_cells] = 0
    #
    #     # sim.d_cells_x[cells.nn_bound] = 0
    #     # sim.d_cells_y[cells.nn_bound] = 0
    #
    # else: # create a single fixed point on the boundary to prevent it from floating away
    #
    #     sim.d_cells_x[cells.bflags_cells[0]] = 0
    #     sim.d_cells_y[cells.bflags_cells[0]] = 0


    # check the displacement for NANs:
    stb.check_v(sim.d_cells_x)


def implement_deform_timestep(sim, cells, t, p):
    """
    Implements the deformation of the tissue cluster based on divergence-free deformation
    calculated for cell centres.

    """
    # create a smooth bivariate spline to interpolate deformation data from cells:
    cellinterp_x = SmoothBivariateSpline(cells.cell_centres[:, 0], cells.cell_centres[:, 1], sim.d_cells_x, kx=3, ky=3)
    cellinterp_y = SmoothBivariateSpline(cells.cell_centres[:, 0], cells.cell_centres[:, 1], sim.d_cells_y, kx=3, ky=3)

    # calculate deformations wrt the ecm using the smooth bivariate spline:
    decm_x = cellinterp_x.ev(cells.ecm_verts_unique[:, 0], cells.ecm_verts_unique[:, 1])
    decm_y = cellinterp_y.ev(cells.ecm_verts_unique[:, 0], cells.ecm_verts_unique[:, 1])

    # get the new ecm verts by applying the deformation:
    ecm_x2 = cells.ecm_verts_unique[:, 0] + decm_x
    ecm_y2 = cells.ecm_verts_unique[:, 1] + decm_y

    ecm_new = np.column_stack((ecm_x2, ecm_y2))

    # repackage new ecm vertices as cells.ecm_verts:
    ecm_verts2 = []

    for inds in cells.inds2ecmVerts:
        ecm_verts2.append(ecm_new[inds])

    # cells.ecm_verts = np.asarray(ecm_verts2)

    # rebuild essential portions of the cell world:
    cells.deformWorld(p, ecm_verts2)

    # write data to time-storage vectors:
    sim.cell_centres_time.append(cells.cell_centres[:])
    sim.mem_mids_time.append(cells.mem_mids_flat[:])
    # sim.maskM_time.append(cells.maskM[:])
    sim.mem_edges_time.append(cells.mem_edges_flat[:])
    sim.cell_verts_time.append(cells.cell_verts[:])
