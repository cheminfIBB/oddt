import os
from tempfile import NamedTemporaryFile

from nose.tools import assert_in, assert_not_in, assert_equal
from sklearn.utils.testing import assert_true, assert_array_equal
import pandas as pd

import oddt
import oddt.pandas as opd

test_data_dir = os.path.dirname(os.path.abspath(__file__))


def test_classes():
    """ Test oddt.pandas classes behavior """
    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))

    # Check classes inheritance
    assert_true(isinstance(df, opd.ChemDataFrame))
    assert_true(isinstance(df, pd.DataFrame))
    assert_true(isinstance(df['mol'], opd.ChemSeries))
    assert_true(isinstance(df['mol'], pd.Series))
    assert_true(isinstance(df, pd.DataFrame))

    # Check custom metadata
    assert_true(hasattr(df, '_molecule_column'))
    assert_true(hasattr(df[['mol']], '_molecule_column'))
    assert_equal(df._molecule_column, df[['mol']]._molecule_column)

    # Check if slicing perserve classes
    assert_true(isinstance(df.head(1), opd.ChemDataFrame))
    assert_true(isinstance(df['mol'].head(1), opd.ChemSeries))


def test_reading():
    """ Test reading molecule files to ChemDataFrame """
    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))

    # Check dimensions
    assert_equal(len(df), 100)
    assert_equal(len(df.columns), 15)

    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'),
                      smiles_column='smi_col')
    assert_in('smi_col', df.columns)

    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'),
                      molecule_column=None,
                      molecule_name_column=None,
                      usecols=['name'])
    assert_not_in('mol', df.columns)
    assert_not_in('mol_name', df.columns)
    assert_equal(len(df.columns), 1)

    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'),
                      usecols=['name', 'uniprot_id', 'act'])
    assert_equal(len(df.columns), 5)  # 3 from use_cols + 1 'mol' + 1 'mol_name'
    assert_in('uniprot_id', df.columns)
    assert_not_in('smi_col', df.columns)

    # Chunk reading
    chunks = []
    for chunk in opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'), chunksize=10):
        assert_equal(len(chunk), 10)
        chunks.append(chunk)
    assert_equal(len(chunks), 10)
    df = pd.concat(chunks)

    # Check dimensions
    assert_equal(len(df), 100)


def test_substruct_sim_search():
    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf')).head(10)
    query = oddt.toolkit.readstring('smi', 'C(=O)(N1C[C@H](C[C@H]1C(=O)N[C@@H]1CCCc2c1cccc2)Oc1ccccc1)[C@@H](NC(=O)[C@H](C)NC)C1CCCCC1')

    ge_answear = [True, True, True, False, True, False, False, False, False, False]
    assert_equal((df.mol >= query).tolist(), ge_answear)

    le_answear = [True, True, True, True, True, True, False, False, False, True]
    assert_equal((df.mol <= query).tolist(), le_answear)

    sim = df.mol.calcfp() | query.calcfp()
    assert_equal(sim.dtype, 'float64')


def test_mol2():
    """Writing and reading of mol2 fils to/from ChemDataFrame"""
    if (oddt.toolkit.backend == 'ob' and oddt.toolkit.__version__ >= '2.4.0'):
        df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))
        with NamedTemporaryFile(suffix='.mol2') as f:
            df.to_mol2(f.name)
            df2 = opd.read_mol2(f.name)
            assert_equal(df.shape, df2.shape)
            chunks = []
            for chunk in opd.read_mol2(f.name, chunksize=10):
                assert_equal(len(chunk), 10)
                chunks.append(chunk)
            df3 = pd.concat(chunks)
            assert_equal(df.shape, df3.shape)
        with NamedTemporaryFile(suffix='.mol2') as f:
            df.to_mol2(f.name, columns=['name', 'uniprot_id', 'act'])
            df2 = opd.read_mol2(f.name)
            assert_equal(len(df2.columns), 5)


def test_sdf():
    """Writing ChemDataFrame to SDF molecular files"""
    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))
    with NamedTemporaryFile(suffix='.sdf') as f:
        df.to_sdf(f.name)
        df2 = opd.read_sdf(f.name)
    assert_array_equal(df.columns, df2.columns)
    with NamedTemporaryFile(suffix='.sdf') as f:
        df.to_sdf(f.name, columns=['name', 'uniprot_id', 'act'])
        df2 = opd.read_sdf(f.name)
    assert_equal(len(df2.columns), 5)


def test_csv():
    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'),
                      columns=['mol', 'name', 'chembl_id', 'dude_smiles', 'act'])
    df['act'] = df['act'].astype(float)
    df['name'] = df['name'].astype(int)
    with NamedTemporaryFile(suffix='.csv', mode='w+') as f:
        df.to_csv(f, index=False)
        f.seek(0)
        df2 = opd.read_csv(f, smiles_to_molecule='mol', molecule_column='mol')
    assert_equal(df.shape, df2.shape)
    assert_equal(df.columns.tolist(), df2.columns.tolist())
    assert_equal(df.dtypes.tolist(), df2.dtypes.tolist())


def test_ipython():
    """iPython Notebook molecule rendering in SVG"""
    df = opd.read_sdf(os.path.join(test_data_dir, 'data/dude/xiap/actives_docked.sdf'))
    # mock ipython
    oddt.toolkit.ipython_notebook = True
    # png
    oddt.toolkit.image_backend = 'png'
    html = df.head(1).to_html()
    assert_in('<img src="data:image/png;base64,', html)
    # svg
    oddt.toolkit.image_backend = 'svg'
    html = df.head(1).to_html()
    assert_in('<svg', html)
    oddt.toolkit.ipython_notebook = False
