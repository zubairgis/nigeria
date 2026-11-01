# KoboToolbox polling-agent registration

This package contains an XLSForm and a 176,846-row external polling-unit choice list. The form asks for the agent's name, age, mobile number, state, LGA, ward and polling unit. The location choices cascade from state to LGA to ward to polling unit.

## Deploy

1. Sign in to the NDC's KoboToolbox account and create a project by uploading `ndc_polling_agent_registration.xlsx`.
2. In the project settings, upload `media/polling_units.csv` as an external choice file. Keep this exact filename.
3. Preview the form and verify the state → LGA → ward → polling-unit cascade on web and KoboCollect before deployment.
4. Complete the data-controller contact and retention-period text in the privacy notice before collecting information.
5. Restrict project access to authorized NDC administrators and field coordinators. Export responses only to approved private storage.

The XLSForm follows KoboToolbox's [external-file selection documentation](https://support.kobotoolbox.org/select_from_file_xls.html) and [choice-filter documentation](https://support.kobotoolbox.org/choice_filters_xls.html). The polling-unit file must be uploaded in the Kobo project media settings; it is not automatically loaded by GitHub.

## Privacy

Name, age and phone number are personal information in a political-organization context. Store response data in the private Kobo project. Do not commit response exports, credentials, or individual agent details to this public repository. The controller/contact and retention details are deployment fields because they were not provided here; the form should not be deployed to collect real data until those fields are filled in.
