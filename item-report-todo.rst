========================
Item Report support TODO
========================

What remains to be done:

* [x] implement item view for a platform
* [x] implement item view for a title
* [x] item view set
  - [x] filter by date
  - [x] include interest
* [x] item detail view
  - [x] charts
  - [x] authors
* [-] add support for items into reporting
     (should only appear if item report is seleted; also PR should not have title visible)
     - we better wait for the new reporting to be implemented, we do not want to do it twice
* [-] add definition of IR_A1 and IR_M1 views - probably wait until we somehow migrate IR_M1 to IR
* [/] interest - separate chapter for that
  - [x] when ingesting IR, interest from TR should be removed (accomplished by marking TR as obsoleted by IR)
    - [x] when replacing interest from TR with IR, we should also remove the corresponding materialized TR views
  - [x] create a script which will create the interest settings for IR
      - [x] add interest metrics to the IR report type
      - [x] make IR a default report type for interest
  - [x] create a migration which will update `interest_no_title` to also exclude items,
        add `interest_no_item` to only exclude items
* [x] pub_type - we need the same mechanism for assigning pub_type as we have for titles
* [x] some platforms do not honor the `include_parent_details` attr and do not include info about
      the title corresponding to the item. Such data cannot be used for interest computation on the
      title level, so we should raise an error when ingesting such data to cause the RT to be
      marked as broken and the user will know that it cannot be used.
      **BUT** - this is only true for article related data - for multimedia, it is normal to have
      items without a title (directly under the platform).
* [x] be less strict about data in the report:
  - [x] `Publication_Date` from Bloomsbury contains "-" which is invalid, but we could interpret it
        as publication date not being available and completely ignore it


Interest
--------

In order to have interest on item level, we need to use IR report for interest computation. But
in such cases, we need **not to** use TR for interest as well, as it would be double-counting.

The situation is similar to TR and PR reports. There are a few problems with this approach:

* interest for titles will be split into many rows (one for each item), so queries will be slower
  (small test with BioOne data for one month showed 78->450 rows increase). But we can mitigate
  that by using a materialized RT with `item_id` dropped.
* we need to trust that the IR covers all of TR data.
  Update: Experiments on BioOne show that it is not always the case. The two main problems are:
  - `No_License` is not reported in the IR report (14/16 hits in difference)
  - Records with YOP equal to `0001` are not reported in the IR report (2/16 hits of difference)

Heretic question: would it be possible to drop TR if we have IR? We should be able to compute the
TR report from IR data...

We may also want to encode the source of the interest (IR or TR) into the data, so we can later
debug it (for now we use the metric remapping, which may be useful, but we could also add extra
dimension for that with the source report type information).


Multimedia problem
++++++++++++++++++

At present, we use `IR_M1` for multimedia interest computation. But `IR_M1` is just a view of `IR`
with `Data_Type` set to `Multimedia`. So we cannot naively use the whole `IR` for `full_text`
interest computation, as it would include multimedia items.

This means that we should split the data from `IR` into two parts based on the `Data_Type`.
Also, we should probably drop `Data_Type=Multimedia` from interest calculated from `TR` because
`Multimedia` can appear in `TR` as well (even though we are not sure how and why :D).



In production
-------------

Run::

  python manage.py check_report_type_dimensions --fix-it

Materialized views for Interest which drop titles should drop items as well, otherwise they would be
useless.
