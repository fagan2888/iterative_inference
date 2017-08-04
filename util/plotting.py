import visdom
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

global vis


def init_plot(train_config, arch, env='main', port=8097):
    vis = initialize_env(env, port)
    plot_config(train_config, arch)
    handle_dict = initialize_plots(train_config, arch)
    return vis, handle_dict


def initialize_env(env='main', port=8097):
    """Creates a visdom environment."""
    global vis
    vis = visdom.Visdom(port=port, env=env)
    return vis


def initialize_plots(train_config, arch):
    nans = np.zeros((1, 2), dtype=float)
    nans.fill(np.nan)

    # plots for average metrics on train and validation set
    kl_legend = []
    for mode in ['Train', 'Validation']:
        for level in range(len(arch['n_latent'])):
            kl_legend.append(mode + ', Level ' + str(level))
    kl_nans = np.zeros((1, 2 * len(arch['n_latent'])))
    kl_nans.fill(np.nan)
    elbo_handle = plot_line(nans, np.ones((1, 2)), legend=['Train', 'Validation'], title='ELBO', xlabel='Epochs', ylabel='-ELBO (Nats)', xformat='log', yformat='log')
    cond_log_like_handle = plot_line(nans, np.ones((1, 2)), legend=['Train', 'Validation'], title='Conditional Log Likelihood', xlabel='Epochs', ylabel='-log P(x | z) (Nats)', xformat='log', yformat='log')
    kl_handle = plot_line(kl_nans, np.ones((1, 2 * len(arch['n_latent']))), legend=kl_legend, title='KL Divergence', xlabel='Epochs', ylabel='KL(q || p) (Nats)', xformat='log', yformat='log')

    handle_dict = dict(elbo=elbo_handle, cond_log_like=cond_log_like_handle, kl=kl_handle)

    if train_config['n_iterations'] > 1:
        # plot of average improvement over iterations on validation set
        kl_legend = []

        for level in range(len(arch['n_latent'])):
            kl_legend.append('Level ' + str(level))

        if len(arch['n_latent']) > 1:
            kl_nans = np.zeros((1, len(arch['n_latent'])))
            kl_nans.fill(np.nan)
            indices = np.ones((1, len(arch['n_latent'])))
        else:
            kl_nans = np.array(np.nan).reshape(1)
            indices = np.ones(1)

        elbo_improvement_handle = plot_line(np.array(np.nan).reshape(1), np.ones(1), legend=['ELBO'], title='Ave. Improvement in ELBO Over Inference Iterations', xlabel='Epochs', ylabel='Relative Improvement (%)', xformat='log')
        recon_improvement_handle = plot_line(np.array(np.nan).reshape(1), np.ones(1), legend=['log P(x | z)'], title='Ave. Improvement in Reconstruction Over Inference Iterations', xlabel='Epochs', ylabel='Relative Improvement (%)', xformat='log')
        kl_improvement_handle = plot_line(kl_nans, indices, legend=kl_legend, title='Ave. Improvement in KL Divergence Over Inference Iterations', xlabel='Epochs', ylabel='Relative Improvement (%)', xformat='log')

        handle_dict['elbo_improvement'] = elbo_improvement_handle
        handle_dict['recon_improvement'] = recon_improvement_handle
        handle_dict['kl_improvement'] = kl_improvement_handle

    return handle_dict



def save_env():
    """Saves the visdom environment."""
    global vis
    vis.save([vis.env])


def plot_config(train_config, arch):
    """Wraps visdom's text box to display train config and model architecture."""
    global vis
    config_string = 'Train Config: '
    for config_item in train_config:
        config_string += str(config_item) + ' = ' + str(train_config[config_item]) + ', '
    model_string = 'Model Architecture: '
    for arch_item in arch:
        model_string += str(arch_item) + ' = ' + str(arch[arch_item]) + ', '

    config_win = vis.text(config_string)
    model_win = vis.text(model_string)
    return config_win, model_win


def plot_images(imgs, caption=''):
    """Wraps visdom's image and images functions."""
    global vis
    if len(imgs.shape) == 3:
        imgs = np.expand_dims(imgs, axis=0)
    if imgs.shape[-1] == 3 or imgs.shape[-1] == 1:
        imgs = imgs.transpose((0, 3, 1, 2))
    opts = dict(caption=caption)
    win = vis.images(imgs, opts=opts)
    return win


def plot_video(video, fps=1):
    """Wraps visdom's video function."""
    global vis
    opts = dict(fps=int(fps))
    win = vis.video(video, opts=opts)
    return win


def plot_line(Y, X=None, legend=None, win=None, title='', xlabel='', ylabel='', xformat='linear', yformat='linear'):
    """Wraps visdom's line function."""
    global vis
    opts = dict(title=title, xlabel=xlabel, ylabel=ylabel, legend=legend, xtype=xformat, ytype=yformat)
    if win is None:
        win = vis.line(Y, X, opts=opts)
    else:
        win = vis.line(Y, X, win=win, opts=opts, update='append')
    return win


def update_trace(Y, X, win, name):
    """Wraps visdom's updateTrace function."""
    global vis
    vis.updateTrace(X, Y, win=win, name=name)


def plot_scatter(X, Y=None, legend=None, title='', xlabel='', ylabel='', markersize=5):
    """Wraps visdom's scatter function."""
    global vis
    opts = dict(title=title, xlabel=xlabel, ylabel=ylabel, markersize=markersize)
    win = vis.scatter(X, Y, opts=opts)
    return win


def plot_pca(data, labels=None, n_dims=3, title='', legend=None):
    """PCA visualization of high-dimensional state data."""
    assert n_dims in [2, 3], 'n_dims must be 2 or 3'
    data = data.reshape((-1, np.prod(data.shape[1:])))
    pca = PCA(n_components=n_dims).fit(data)
    pca_data = pca.transform(data)
    plot_scatter(pca_data, labels, legend=legend, title=title)


def plot_tsne(data, labels=None, n_dims=3, title='', legend=None):
    """T-SNE visualization of high-dimensional state data."""
    assert n_dims in [2, 3], 'n_dims must be 2 or 3'
    data = data.reshape((-1, np.prod(data.shape[1:])))
    if data.shape[1] > 100:
        pca = PCA(n_components=100).fit(data)
        data = pca.transform(data)
    tsne = TSNE(n_components=n_dims)
    tsne_data = tsne.fit_transform(data)
    plot_scatter(tsne_data, labels, legend=legend, title=title)


def plot_train(func):
    """Wrapper around training function to plot the outputs in corresponding visdom windows."""
    def plotting_func(model, train_config, data, epoch, handle_dict, optimizers):
        output = func(model, train_config, data, epoch, optimizers)
        avg_elbo, avg_cond_log_like, avg_kl = output
        update_trace(np.array([-avg_elbo]), np.array([epoch]).astype(int), win=handle_dict['elbo'], name='Train')
        update_trace(np.array([-avg_cond_log_like]), np.array([epoch]).astype(int), win=handle_dict['cond_log_like'], name='Train')
        for level in range(len(model.levels)):
            update_trace(np.array([avg_kl[level]]), np.array([epoch]).astype(int), win=handle_dict['kl'], name='Train, Level ' + str(level))
        return output, handle_dict
    return plotting_func


def plot_model_vis(func):
    """Wrapper around run function to plot the outputs in corresponding visdom windows."""
    def plotting_func(model, train_config, data_loader, epoch, handle_dict, vis=True):
        output = func(model, train_config, data_loader, epoch, vis=vis)
        total_elbo, total_cond_log_like, total_kl, total_labels, total_recon, total_posterior, total_prior, samples = output

        # plot average metrics on validation set
        update_trace(np.array([-np.mean(total_elbo[:, -1], axis=0)]), np.array([epoch]).astype(int), win=handle_dict['elbo'], name='Validation')
        update_trace(np.array([-np.mean(total_cond_log_like[:, -1], axis=0)]), np.array([epoch]).astype(int), win=handle_dict['cond_log_like'], name='Validation')
        for level in range(len(model.levels)):
            update_trace(np.array([np.mean(total_kl[level][:, -1], axis=0)]), np.array([epoch]).astype(int), win=handle_dict['kl'], name='Validation, Level ' + str(level))

        if train_config['n_iterations'] > 1:
            # plot average improvement on metrics over iterations
            elbo_improvement = 100. * np.mean(np.divide(total_elbo[:, 1] - total_elbo[:, -1], total_elbo[:, 1]), axis=0)
            update_trace(np.array([elbo_improvement]), np.array([epoch]).astype(int), win=handle_dict['elbo_improvement'], name='ELBO')

            cond_log_like_improvement = 100. * np.mean(np.divide(total_cond_log_like[:, 1] - total_cond_log_like[:, -1], total_cond_log_like[:, 1]), axis=0)
            update_trace(np.array([cond_log_like_improvement]), np.array([epoch]).astype(int), win=handle_dict['recon_improvement'], name='log P(x | z)')

            for level in range(len(model.levels)):
                kl_improvement = 100. * np.mean(np.divide(total_kl[level][:, 1] - total_kl[level][:, -1], total_kl[level][:, 1]), axis=0)
                update_trace(np.array([kl_improvement]), np.array([epoch]).astype(int), win=handle_dict['kl_improvement'], name='Level ' + str(level))

        if vis:
            # plot reconstructions, samples
            batch_size = train_config['batch_size']
            data_shape = list(next(iter(data_loader))[0].size())[1:]
            plot_images(total_recon[:batch_size, 1].reshape([batch_size]+data_shape), caption='Reconstructions, Epoch ' + str(epoch))
            plot_images(samples.reshape([batch_size]+data_shape), caption='Samples, Epoch ' + str(epoch))

            for level in range(len(model.levels)):
                plot_tsne(total_posterior[level][:, 1, 0], 1 + total_labels, title='T-SNE Posterior Mean, Epoch ' + str(epoch) + ', Level ' + str(level))

        return output, handle_dict
    return plotting_func

