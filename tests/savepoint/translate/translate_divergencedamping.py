from typing import Optional

from ndsl import Namelist, StencilFactory
from ndsl.constants import Z_DIM
from pyFV3.stencils import DivergenceDamping
from pyFV3.testing import TranslateDycoreFortranData2Py


class TranslateDivergenceDamping(TranslateDycoreFortranData2Py):
    def __init__(
        self,
        grid,
        namelist: Namelist,
        stencil_factory: StencilFactory,
    ):
        super().__init__(grid, namelist, stencil_factory)
        self.in_vars["data_vars"] = {
            "u": {},
            "v": {},
            "va": {},
            "damped_rel_vort_bgrid": {"serialname": "vort"},
            "ua": {},
            "divg_d": {},
            "vc": {},
            "uc": {},
            "delpc": {},
            "ke": {},
            "rel_vort_agrid": {"serialname": "wk"},
            "nord_col": {},
            "d2_bg": {},
        }
        self.in_vars["parameters"] = ["dt"]
        self.out_vars = {
            "ke": {"iend": grid.ied + 1, "jend": grid.jed + 1},
            "delpc": {},
        }
        self.max_error = 1.4e-10
        self.divdamp: Optional[DivergenceDamping] = None
        self.stencil_factory = stencil_factory
        self.namelist = namelist  # type: ignore

    def compute_from_storage(self, inputs):
        nord_col = self.grid.quantity_factory.zeros(dims=[Z_DIM], units="unknown")
        nord_col.data[:] = nord_col.np.asarray(inputs.pop("nord_col"))
        d2_bg = self.grid.quantity_factory.zeros(dims=[Z_DIM], units="unknown")
        d2_bg.data[:] = d2_bg.np.asarray(inputs.pop("d2_bg"))
        self.divdamp = DivergenceDamping(
            self.stencil_factory,
            self.grid.quantity_factory,
            self.grid.grid_data,
            self.grid.damping_coefficients,
            self.grid.nested,
            self.grid.stretched_grid,
            self.namelist.dddmp,
            self.namelist.d4_bg,
            self.namelist.nord,
            self.namelist.grid_type,
            nord_col,
            d2_bg,
        )
        self.divdamp(**inputs)
        return inputs
