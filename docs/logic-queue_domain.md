Processing the queue_domain will either result in:

* AcmeOrder - pending
* AcmeOrder - valid/invalid

																												   
									   +----------------+                                                              
									   |                |                                                              
									   >  create_order  -\       +-------------------+                                 
									 -/|                | --\    |                   |      +-------------------------+
									/  +----------------+    --\ |   AcmeOrder       |      |                         |
								  -/                            ->   pending         -------> acme-order/{id}/process |
	+-------------------------+  /     +----------------+    --/ |                   |      +------------|------------+
	|                         |-/      |                | --/    +-------------------+                   |             
	|  queue-domains/process  ---------> process_multi  -/                                               |             
	|                         |-\      |                |                                                |             
	+-------------------------+  -\    +----------------+                                                |             
								   -\                                                          +---------v---------+   
									 -\+----------------+                                      |                   |   
									   >                |                                      |                   |   
									   | process_single --------------------------------------->    AcmeOrder      |   
									   |                |                                      |  valid/invalid    |   
									   +----------------+                                      |                   |   
																							   +-------------------+   
																												   
																												   
																												   
																												   
																												   