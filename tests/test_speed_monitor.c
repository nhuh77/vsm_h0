/* test_speed_monitor.c - 차속 판정 요구사항 테스트 (스위트 test_speed_monitor)
 *
 * 지금은 러너가 도는지 보는 스모크 케이스 하나만 있다. 요구사항(SR) 별 케이스는 실습에서 이 파일에 더한다.
 * 판정 케이스는 brake_on = false 로 부른다 (제동이 등급에 주는 영향은 요구사항에 없다).
 */

#include "vsm_test.h"
#include "speed_monitor.h"

/* SR-003: 150 km/h 초과 200 km/h 미만 -> MID */
static void sr003_speed_151_is_mid(void)
{
    VT_CHECK_EQ_INT(VSM_WARN_MID, sm_evaluate(151u, false));
}

/* SR-012: 100 -> 60 */
static void sr012_100_to_60_is_drop(void)
{
    VT_CHECK(sm_is_sudden_drop(100u, 60u));
}

/* SR-012: 100 -> 90 */
static void sr012_100_to_90_is_not_drop(void)
{
    VT_CHECK(!sm_is_sudden_drop(100u, 90u));
}

/* SR-012: 60 -> 100 */
static void sr012_60_to_100_is_not_drop(void)
{
    VT_CHECK(!sm_is_sudden_drop(60u, 100u));
}

/* SR-012: 100 -> 70 */
static void sr012_100_to_70_boundary_30_is_drop(void)
{
    VT_CHECK(sm_is_sudden_drop(100u, 70u));
}

/* SR-012: 100 -> 71 */
static void sr012_100_to_71_boundary_29_is_not_drop(void)
{
    VT_CHECK(!sm_is_sudden_drop(100u, 71u));
}

/* SR-012: 100 -> 100 */
static void sr012_100_to_100_is_not_drop(void)
{
    VT_CHECK(!sm_is_sudden_drop(100u, 100u));
}

/* SR-012: 0 -> 0 */
static void sr012_0_to_0_is_not_drop(void)
{
    VT_CHECK(!sm_is_sudden_drop(0u, 0u));
}

/* SR-012: 65535 -> 0 */
static void sr012_65535_to_0_is_drop(void)
{
    VT_CHECK(sm_is_sudden_drop(65535u, 0u));
}

/* SR-012: 0 -> 65535 */
static void sr012_0_to_65535_is_not_drop(void)
{
    VT_CHECK(!sm_is_sudden_drop(0u, 65535u));
}

int main(void)
{
    vt_begin("test_speed_monitor", "test-results/test_speed_monitor.xml");
    vt_run("SR-003_speed_151_is_mid", sr003_speed_151_is_mid);
    vt_run("SR-012_100_to_60_is_drop", sr012_100_to_60_is_drop);
    vt_run("SR-012_100_to_90_is_not_drop", sr012_100_to_90_is_not_drop);
    vt_run("SR-012_60_to_100_is_not_drop", sr012_60_to_100_is_not_drop);
    vt_run("SR-012_100_to_70_boundary_30_is_drop", sr012_100_to_70_boundary_30_is_drop);
    vt_run("SR-012_100_to_71_boundary_29_is_not_drop", sr012_100_to_71_boundary_29_is_not_drop);
    vt_run("SR-012_100_to_100_is_not_drop", sr012_100_to_100_is_not_drop);
    vt_run("SR-012_0_to_0_is_not_drop", sr012_0_to_0_is_not_drop);
    vt_run("SR-012_65535_to_0_is_drop", sr012_65535_to_0_is_drop);
    vt_run("SR-012_0_to_65535_is_not_drop", sr012_0_to_65535_is_not_drop);
    return vt_end() == 0 ? 0 : 1;
}
