============
Interest 2.0
============

Main features
=============

* the same for all platforms - no need to assign reports to platform
* interest type stored in metrics, not dimension
* split by following dimensions:
  * original report type
  * original metric
  * Access_Type - either Controlled or Open
  * Access_Method - either Normal or TDM
* different types of interest will be calculable from the same RT and Metric
  using different filters (necessary to get `Full text` and `Multimedia` interest from the IR report
  - with filter on ``Data_Type``)
* for COUNTER reports, there will be a set hierarchy of reports defining their precedence for
  purposes of interest calculation.
  - finer granularity will have the highest precedence
  - if the granularity is the same, newest COUNTER version will have precedence
  - so IR51 > IR50 > TR51 > TR50
* all reports will define interest by marking metrics as "interest defining"
  - this does not change. But the report will not have to be manually assigned to a platform.
* it will be possible to set on organization level if `Total` or `Unique` metrics should be used
  for interest computation
* user should be able to set preferences if he wants to see interest filtered by either `Access_Type`
  or `Access_Method` by default. This setting will be on organization level, not on individual user level.
  A change will not require a recompuation of the interest.

Implementation notes
====================

* each ImportBatch should have ``interest_ib`` field which will be ForeignKey to ImportBatch.
  If the interest is contained directly in the ImportBatch, it should be set to itself.
  If the interest is not stored in the ImportBatch, then there must be a different ImportBatch
  which is overriding the interest of this one. In this case ``interest_ib`` should be set to
  that ImportBatch.
  This ForeignKey will use ``on_delete=SET_NULL`` and ``null=True`` and thus will allow quick
  detection of deleted ImportBatches for which the interest should be recalculated.

* it will be possible to set which metrics are interest defining on an organization level by
  assigning the ReportType-Metric link to a specific InterestProfile. In such cases, this metric
  will only be used if the InterestProfile is active (either for that organization or the default)

* to describe how incomming data should be mapped to the interest `Access_Method` and `Access_Type`,
  the ReportType-Dimension link between interest and that dimension will have associated
  `InterestDimensionValueMapping`. This will define the default value for such dimension if no
  extra specification is used. If an extra `InterestDimensionValueMapping` is present which connects
  the ReportType-Dimension of interest with ReportType-Dimension of the source ReportType, it will
  be used for mapping (it contains a default value and a mapping dictionary).

* to allow computation of more than one type of interest from one source ReportType, the
  `ReportInterestMetric` can have linked filters which describe how the source data should be filtered
  to get that specific type of interest. For example in case or IR a filter on `Data_Type` will be used.

* PR will not be used for interest computation. See the discussion below in `How to deal with PR`_


How to deal with PR
===================

If we wanted to add PR to the interest computation, we would need to change the whole structure
of the interest computation. PR is superseded by not one but two report types: DR and TR.
It can also contain several different types of interest - Full Text, Search, Multimedia + denials.

Thus interest from PR could be only partially replaced by TR, while search and multimedia interest
would still remain in the PR. To support this, we would need the following changes:

* superseding links would not be direct, but contain link to the interest group as well
* when searching for superseding report types, we would need to search by interest group
* thus the whole computation of interest would need to be split by interest group from early
  on in the code
* link from IB to interest IB would have to be changed to an extra linking model
  (but the idea of using SET_NULL would still apply - we would just search for linking models
   with null ``interest_ib``)
