# Adoption metrics: definitions and the decisions they drive

A rollout is funded to produce a business result. Adoption is the leading indicator of that result, and it is measurable weeks before the result is. These are the metrics I hold a platform rollout to, grouped the way a sponsor thinks about them: are people starting, are they staying, are they using it well, and is the work actually moving to the new way.

Every metric has an owner, a cadence, a target that is set before go-live, and the decision it exists to trigger. A metric without a decision attached is reporting, not management.

## The vital few (the headline three)

| Metric | Definition | Target shape | Decision it triggers |
|---|---|---|---|
| **Weekly active users by group** | Share of the impacted population in each group who performed at least one core action in the platform in the week. Core actions are defined per group before go-live (for a decisioning platform: authored, approved, or deployed an action or treatment; reviewed engine results). | Ramp curve per group: e.g. 30% by week 2, 60% by week 6, 80% by week 10. The curve is set with the group's leader and is theirs. | A group more than one stage behind its curve for two consecutive weeks gets a readiness re-score and a sponsor conversation with the group's leader. |
| **Time to first use** | Days from a user's access date to their first core action. Reported as median and 80th percentile per group. | Median under 10 days; 80th percentile under 21. | A long tail (80th percentile stretching while the median holds) means access was granted without a reason to log in; fix the trigger (a live task, a manager ask), not the training. |
| **Work migrated** | Share of the group's real work volume flowing through the new platform rather than the legacy path. For a campaign platform: campaigns deployed through the engine as a share of all campaigns deployed. | 50% by first-wave month 3, 90% by month 6, legacy path closed by month 9. | Below target with high active-user rates means people log in but keep the old path for the work that matters. That is a Desire or Ability barrier, and the legacy path's retirement date is the lever. |

## Supporting metrics

| Metric | Definition | Why it matters | Decision it triggers |
|---|---|---|---|
| **Retention (week-over-week return)** | Of users active in week N, share active in week N+1. | Separates a launch spike from a habit. | Retention under 70% in a group with good first-use numbers means the tool is not yet part of the workflow; look at manager reinforcement. |
| **Feature depth** | Average number of distinct core actions per active user per week, or share of active users who used two or more core actions. | Shallow use (log in, look, leave) is compliance, not adoption. | Depth flat while active users climb means training covered the login and not the job. |
| **Self-service rate** | Share of tasks completed without a ticket, office-hours visit, or hand-hold from the core team. | The core team is the bottleneck in every rollout; this is the measure of whether capacity is being handed back. | Self-service below 60% at month 3 keeps the core team in support mode and delays the next wave. |
| **Support-ticket rate per active user** | Tickets opened per 100 active users per week, split into access, how-to, and defect. | How-to tickets should fall; defect tickets should fall faster. | How-to tickets rising with active users is normal for four weeks, then a training gap. Access tickets at all after week 2 are a provisioning failure. |
| **Override or bypass rate** | Platform-specific: share of model recommendations overridden, or share of items built with the legacy method inside the new tool. | The most honest Desire signal there is. | An override rate above the agreed guardrail with no documented reason is the first conversation with the group's manager. |
| **Manager coaching touchpoints** | Share of people managers who held a documented conversation about the change with each direct report in the period. | Reinforcement lives with the direct manager, not the project team. | Below 50% in a group that is lagging means the toolkit is not being used; the sponsor's ask goes to the manager's leader. |

## What "adopted" means

A group is adopted when, for four consecutive weeks: weekly active users are at or above the target plateau, work migrated is at or above 80%, and the override rate is inside the guardrail. Adoption is declared per group and per unit, never for the program as a whole, because the program average hides the unit that is stalling.

## Reading the numbers

- **Active users up, work migrated flat.** People are in the tool and not doing the real work there. Desire barrier; check the legacy path and the override rate.
- **Active users up, retention down.** Launch spike. Reinforcement barrier; check manager touchpoints.
- **Time-to-first-use median fine, 80th percentile long.** Access without a trigger. Give every user a live task in week one.
- **Self-service low, tickets high, active users high.** Ability barrier; the training did not match the job. Look at feature depth to see which actions people avoid.
- **One group behind on everything.** Look at that group's sponsor before looking at that group.
