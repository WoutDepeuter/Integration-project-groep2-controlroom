FROM docker.elastic.co/beats/metricbeat:9.0.0
COPY --chown=root:metricbeat conf.yml /usr/share/metricbeat/metricbeat.yml
RUN chmod go-w /usr/share/metricbeat/metricbeat.yml