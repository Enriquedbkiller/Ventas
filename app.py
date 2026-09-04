KeyError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/ventas/app.py", line 767, in <module>
    procesar_dataframe(df_acumulada, "📈 Vista de Venta Acumulada")
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/mount/src/ventas/app.py", line 603, in procesar_dataframe
    temp_source.groupby("División")
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/util/_decorators.py", line 336, in wrapper
    return func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/frame.py", line 10835, in groupby
    return DataFrameGroupBy(
        obj=self,
    ...<6 lines>...
        dropna=dropna,
    )
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/groupby/groupby.py", line 1095, in __init__
    grouper, exclusions, obj = get_grouper(
                               ~~~~~~~~~~~^
        obj,
        ^^^^
    ...<4 lines>...
        dropna=self.dropna,
        ^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/groupby/grouper.py", line 901, in get_grouper
    raise KeyError(gpr)
