# Jira2Gus

# Basic How-To

## Prepare:

```bash
pip install -r requirements.txt
```

Setup the following vars:

* gus_server ( example gus--ma.my.salesforce.com)
* gus_user (example datorama_integration@gus.com.ma)
* gus_password (example 1234gh12)
* cloud_id - the id for the company cloud in gus.
* chatter_group - the id for a dedicated migration chatter group for file attachments - (example 0F92g000000CnofCAC)
* default_assignee - a user id in gus for default assigne for cases where we have to have an assignee and we were not provided a valid gus user. (in the form of `005B0000006LzFNIA0`)
* default_build - a build id in gus for cases where we must have a build.
* jira server (example jira_server=https://jira.datorama.net)
* jira user (example qa_automation)
* jira password (example 1234gh12)
* epic_field - the full API name of the epic link field(ex: customfield_10940)
* overwrite (true or false)

There are 3 ways we migrate stuff: 
* single migration - jira_query, product_tag, mapping_key overwrite - migrate a single jira_query into a product_tag using the corresponding mapping configuration - will also migrate attachments.
* multi migration - job_key - the job key is the name of a csv file which holds multiple rows of single migrations, the job will serially run the migrations - will not migrate attachments (as attachments take a long time to migrate).
* attachments migration -  jira_query - looks for work items that originated from issues that were found by the jira query and if found it will migrate the attachments.

The mapping key, which is also set up in mapping_key env var will search for things under `./mapping/[mapping_key]/` for mapping information.

# Known issues

## the use of &

A `&` in `gus_password` will make the script fail with:

```bash
Exception: Login Failed <?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><soapenv:Fault><faultcode>soapenv:Client</faultcode><faultstring>The entity name must immediately follow the &apos;&amp;&apos; in the entity reference.</faultstring></soapenv:Fault></soapenv:Body></soapenv:Envelope>
```

# example launch.json

An example launch.json for sandbox testing would be something like this:

```json
{
  // Use IntelliSense to learn about possible attributes.
  // Hover to view descriptions of existing attributes.
  // For more information, visit: https://go.microsoft.com/fwlink/?linkid","value":"830387
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "scripts/single.py",
      "console": "integratedTerminal",
      "env":{
        "gus_server":"gus--ma.my.salesforce.com",
        "gus_user":"myGusUser@gus.com.ma",
        "gus_password":"notTheRealPass",
        "jira_server":"https://www.mulesoft.org/jira",
        "jira_user":"bot-SDLCT-3561-gusmigration",
        "jira_password":"notTheRealPass",
        "default_assignee":"005B0000006LzFNIA0",
        "default_build":"a06AG0000000EnlYAE",
        "gus_cloud_id":"a3mB000000022K7IAI",
        "chatter_group":"0F9AG00000000Cv0AI",
        "product_tag":"a1aB0000000UEs8IAG",
        "jira_query":"key in (EST-792)",
        "mapping_key":"mstest",
        "overwrite":"false",
        "jira_epic_column_id":"customfield_10940",
        "jira_sprint_column_id":"customfield_10640"
      }
    }
  ]
}
```

# Hey!, I want docker!

Wait!, I'll get there bro!
