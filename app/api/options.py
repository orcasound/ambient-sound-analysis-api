from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.responses import OptionsResponse
from app.services.get_options import (
    OptionsDependencyError,
    OptionsLookupError,
    get_options,
)


router = APIRouter(tags=["options"])


# request per hydrophone for fastest response, or leave blank for all hydrophones (slow)
@router.get("/options", response_model=OptionsResponse)
def list_options(
    hydrophone: Optional[str] = Query(
        None, description="Optional hydrophone name, e.g. bush_point."
    )
) -> OptionsResponse:
    try:
        return get_options(hydrophone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OptionsLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

# options response properties from orcasound_noise:
# - `delta_ts` -- available time resolutions, i.e. 1 second, maps to delta_t in pipeline
# - `delta_fs` -- available linear or octave band intervals, i.e. 1/3 octave or 1 Hz linear
# - `freq_types` -- broadband is always available, the other types are `octave_band` or `delta_hz` (linear)

# example: hydrophone='orcasound_lab' delta_ts=[1] delta_fs=[3] freq_types=['broadband', 'octave_bands']

# call this in NoiseAccessor as delta_t={delta_ts} and delta_f={freq_type}
# freq_type: 'broadband' = 'broadband'; 'octave_bands / 3' = '3oct'; 'delta_hz / 1' = '1hz'
