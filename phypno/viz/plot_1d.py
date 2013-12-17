from visvis import plot, use

# use('qt4')


def plot_data(data, xaxis='time', xlog=False, ylog=False):
    """Plot data in 2d.

    """
    xval = getattr(data, xaxis)
    for i_ch in range(len(data.chan_name)):
        plot(xval, data.data[i_ch, :])
