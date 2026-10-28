/* speed_monitor.h - 차속 기반 경고 등급 판정 */

#ifndef VSM_SPEED_MONITOR_H
#define VSM_SPEED_MONITOR_H

#include "vsm_types.h"

/* 급감속 판정 기준: 직전 대비 감소량 (SR-012) */
#define VSM_SUDDEN_DROP_KPH 30u

/* 현재 차속과 제동 상태로 경고 등급을 판정한다 (SR-002, SR-003) */
vsm_warn_t sm_evaluate(uint16_t speed_kph, bool brake_on);

/* 과속 카운터를 초기화한다 (SR-005) */
void sm_reset(uint16_t ecu_id);

/* 누적 과속 횟수를 반환한다 */
uint32_t sm_over_count(void);

/* 직전 차속 대비 감소량이 VSM_SUDDEN_DROP_KPH 이상이면 true (SR-012) */
bool sm_is_sudden_drop(uint16_t prev_kph, uint16_t curr_kph);

#endif /* VSM_SPEED_MONITOR_H */
