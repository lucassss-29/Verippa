import streamlit as st
import time
import collections.abc


def update_workflow_status(ui, label, message='', state='running', expanded=False, persist=False):

    # status_box = ui.get('log_status')

    # if status_box is not None:
    with ui['log_status'] as status_box:
        is_an_iterator = isinstance(message, collections.abc.Iterator)

        if is_an_iterator:

            # verbose_box = st.container(height=250, autoscroll=True)

            with ui['verbose']:

                # stream_instance = yield_stream_generator(message)
                stream_instance = message

                print('state: ', state)

                status_box.update(label=label, expanded=True, state='running')

                st.write_stream(stream_instance)

        elif message:

            with ui['verbose']:

                status_box.update(label=label, expanded=True)

                st.write(message)

                if persist == False:

                    time.sleep(1.5)

        status_box.update(label=label, state=state, expanded=expanded)