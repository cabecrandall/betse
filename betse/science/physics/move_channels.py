#!/usr/bin/env python3
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

import numpy as np


def eosmosis(sim, cells, p):
    """
    Movement of ion pumps and channels to potentially create directional fluxes in individual cells.

    This is presently simulated by calculating the Nernst-Planck concentration flux of a weighting
    agent, rho, which moves under its own concentration gradient (a homogeneity restoring influence)
    as well as under the influence of the extracellular voltage gradient and fluid flows tangential
    to the membrane.

    """

    # x and y components of membrane tangent unit vectors
    tx = cells.mem_vects_flat[:, 4]
    ty = cells.mem_vects_flat[:, 5]

    # # tangential components of fluid flow velocity at the membrane, if applicable:
    # if p.fluid_flow is True and p.sim_ECM is True:
    #     # map the flow vectors to membrane midpoints
    #     ux_mem = sim.u_env_x.ravel()[cells.map_mem2ecm]
    #     uy_mem = sim.u_env_y.ravel()[cells.map_mem2ecm]
    #
    #     # tangential component of fluid velocity at membrane:
    #     u_tang = ux_mem*tx + uy_mem*ty
    #
    # elif p.fluid_flow is True and p.sim_ECM is False:
    #
    #     # map the flow vectors to membrane midpoints
    #     ux_mem = sim.u_cells_x[cells.mem_to_cells]
    #     uy_mem = sim.u_cells_y[cells.mem_to_cells]
    #
    #     # normal component of fluid velocity at membrane:
    #     u_tang = ux_mem * tx + uy_mem * ty
    #
    # else:
    #     u_tang = 0
    #
    # map rho pump and rho channel to cell vertices:
    pump_at_verts = np.dot(sim.rho_pump, cells.matrixMap2Verts)
    channel_at_verts = np.dot(sim.rho_channel, cells.matrixMap2Verts)

    # get the gradient of rho concentration around each membrane:
    grad_c_p =  np.dot(cells.gradMem, pump_at_verts)
    grad_c_ch = np.dot(cells.gradMem, channel_at_verts)
    #
    # # get the tangential electric field at each membrane
    # if p.sim_ECM is True:
    #
    #     Ex = sim.E_env_x.ravel()[cells.map_mem2ecm]
    #     Ey = sim.E_env_y.ravel()[cells.map_mem2ecm]
    #
    #     # get the tangential component to the membrane:
    #     E_tang = Ex * tx + Ey * ty
    #
    # else:  # if not simulating extracellular spaces, then use the intracellular field instead:
    #     # Ex = sim.J_cell_x[cells.mem_to_cells]
    #     # Ey = sim.J_cell_y[cells.mem_to_cells]
    #     #
    #     # # get the normal component to the membrane:
    #     # E_tang = (Ex * tx + Ey * ty)*p.media_sigma

    # Ex = (np.dot(cells.M_sum_mems, sim.E_gj_x)/cells.num_mems)[cells.mem_to_cells]
    # Ey = (np.dot(cells.M_sum_mems, sim.E_gj_y)/cells.num_mems)[cells.mem_to_cells]
    Ex = p.media_sigma*sim.J_cell_x[cells.mem_to_cells]
    Ey = p.media_sigma*sim.J_cell_y[cells.mem_to_cells]

    E_tang = (Ex * tx + Ey * ty)


    # calculate the total Nernst-Planck flux at each membrane for rho_pump factor:

    flux_pump = -p.D_membrane*grad_c_p  + \
                ((p.z_pump*p.D_membrane*p.F)/(p.R*p.T))*sim.rho_pump*E_tang

    flux_chan = -p.D_membrane * grad_c_ch  * sim.rho_channel + \
                ((p.z_channel * p.D_membrane * p.F) / (p.R * p.T)) * sim.rho_channel * E_tang


    # divergence of the total flux via dfx/dx + dfy/dy:
    # components of flux in x and y directions, mapped to cell verts:
    # pumps:
    gfx_p = np.dot(-flux_pump * tx, cells.matrixMap2Verts)
    gfy_p = np.dot(-flux_pump * ty, cells.matrixMap2Verts)

    ddfx_p = np.dot(cells.gradMem, gfx_p) * tx
    ddfy_p = np.dot(cells.gradMem, gfy_p) * ty

    divF_pump = ddfx_p + ddfy_p


    gfx_ch = np.dot(-flux_chan * tx, cells.matrixMap2Verts)
    gfy_ch = np.dot(-flux_chan * ty, cells.matrixMap2Verts)

    ddfx_ch = np.dot(cells.gradMem, gfx_ch) * tx
    ddfy_ch = np.dot(cells.gradMem, gfy_ch) * ty

    divF_chan = ddfx_ch + ddfy_ch

    sim.rho_pump = sim.rho_pump - divF_pump * p.dt*p.gj_acceleration
    sim.rho_channel = sim.rho_channel - divF_chan * p.dt*p.gj_acceleration

    # ------------------------------------------------
    # make sure nothing is non-zero:
    # fix_inds = (sim.rho_pump < 0).nonzero()
    # sim.rho_pump[fix_inds] = 0
    #
    # fix_inds2 = (sim.rho_channel < 0).nonzero()
    # sim.rho_channel[fix_inds2] = 0