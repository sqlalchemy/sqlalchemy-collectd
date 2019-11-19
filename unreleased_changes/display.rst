.. change::
    :tags: feature

    Made large improvements to the connmon display, including a help screen,
    switching between program / host stats, and new stats views.   Overall, as
    connmon is attempting to collect from collectd servers which may also be in
    a network of servers, the "interval" by which messages are received may be
    long, ten seconds by default and much more. To allow a console view to be
    meaningful, new stats are added that illustrate how many connects /
    checkouts have occurred over the last "interval".  That way, even though
    you might never see the current number of "checkouts" go above zero, you
    can at least see that the last ten second interval had 25 checkouts occur.
    The checkouts per second number can be derived from other values shown in
    the display.

