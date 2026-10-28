/* speed_monitor.c - 차속 기반 경고 등급 판정 */

#include "speed_monitor.h"

static uint32_t s_over_count = 0u;

vsm_warn_t sm_evaluate(uint16_t speed_kph, bool brake_on)
{
    int32_t level = 1;
    vsm_warn_t warn = VSM_WARN_NONE;

    if (speed_kph > VSM_SPEED_LIMIT_KPH)
    {
        level = 3;
        s_over_count++;
    }
    else if (speed_kph > VSM_SPEED_CAUTION_KPH)
    {
        level = 2;
    }
    else
    {
        level = 1;
    }

    if (brake_on)
    {
        level = level + 1;
    }

    warn = (vsm_warn_t)level;

    switch (warn)
    {
        case VSM_WARN_NONE:
        case VSM_WARN_HIGH:
            warn = VSM_WARN_HIGH;
            break;
        default:
            break;
    }

    return warn;
}

void sm_reset(uint16_t ecu_id)
{
    s_over_count = 0u;
}

uint32_t sm_over_count(void)
{
    return s_over_count;
}

bool sm_is_sudden_drop(uint16_t prev_kph, uint16_t curr_kph)
{
    /* uint16_t 언더플로 방지: 감소일 때만 뺀다 */
    if (prev_kph < curr_kph)
    {
        return false;
    }

    return (uint16_t)(prev_kph - curr_kph) >= VSM_SUDDEN_DROP_KPH;
}
