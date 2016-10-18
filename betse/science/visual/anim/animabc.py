#!/usr/bin/env python3
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

'''
Abstract base classes of all Matplotlib-based animation subclasses.
'''

#FIXME: Current overlays (as enabled by the "is_current_overlayable" boolean
#and animation-specific configuration options), appear to be broken. In theory,
#refactoring the current overlay approach into a "LayerCellsABC" subclass
#should correct the breakage. Until then, panic stations!

#FIXME: All animations should be displayed in a non-blocking rather than
#blocking manner, as required for parallelizing the animation pipeline. To
#minimize memory leaks while doing so, consider responding to animation window
#close events by explicitly closing the current animation on such events: e.g.,
#
#    def _hook_on_close(event) -> None:
#        print('Animation "{}" window closed.'.format(self._label))
#
#        #FIXME: Is this safe to call here? Presumably, but consider.
#        self._close()
#
#
#    def __init__(...):
#            .
#            -
#            .
#       # Register the close event handler defined above.
#       self._figure.canvas.mpl_connect('close_event', self._hook_on_close)
#            .
#            -
#            .

#FIXME: We should probably animate non-blockingly (e.g., by passing
#"block=False" to the plt.show() command). To do so, however, we'll probably
#have to implement an analogue to Matplotlib's "_pylab_helper.Gcf" global-like
#static class to ensure that object references are retained for all animations
#whose windows have not yet been closed. This implies, in turn, that we'll
#probably have to monkey-patch the appropriate Matplotlib event handlers on
#window close to release these object references. To do so, grep the Matplotlib
#codebase for "Gcf.destroy". Thunderous tales of woe!
#
#Actually, I believe that a simpler approach might be available. Rather
#than implementing yet another "_pylab_helper.Gcf"-like construct, we leverage
#the fact that animation objects should only live as long as their underlying
#figure objects by explicitly adding circular references between the two: e.g.,
#
#    # This is already done by the "VisualCellsABC" superclass.
#    self._figure = pyplot.figure()
#
#    # Then just add this to the AnimCellsABC.__init__() method *BEFORE* the
#    # self._figure.show(block=False) method is called.
#    self._figure.__BETSE_anim__ = self
#
#That said, we might not even need to do that much. Why? Because the
#"FuncAnimation" class is *ALWAYS* passed "self.plot_frame" -- which, being a
#bound method of the current animation object, should ensure that that object
#remains alive. Non-blocking animations may already work out of the box! Oh...
#no. The "FuncAnimation" class is instantiated into an attribute of this class,
#implying that when the last reference to instances of this class go away, they
#everything goes away. We probably will need to add circular references to the
#passed "_figure", as detailed above.
#FIXME: Indeed, a (very minor) amount of research suggests that non-blocking
#animations should be trivially creatable by just ensuring that a reference to
#the instantiated FuncAnimation() object is retained, as intuited above: e.g.,
#
#    https://stackoverflow.com/questions/21099121/python-matplotlib-unable-to-call-funcanimation-from-inside-a-function

# ....................{ IMPORTS                            }....................
import numpy as np
from abc import abstractmethod
from betse.exceptions import BetseParametersException
from betse.lib.matplotlib.matplotlibs import mpl_config
from betse.lib.matplotlib.writer import mplvideo
from betse.lib.matplotlib.writer.mplclass import ImageWriter, NoopWriter
from betse.science.visual.visualabc import VisualCellsABC
from betse.util.io.log import logs
from betse.util.path import dirs, paths
from betse.util.type.types import type_check, NoneType, SequenceTypes
from matplotlib import pyplot
from matplotlib.animation import FuncAnimation
from scipy import interpolate

# ....................{ BASE                               }....................
class AnimCellsABC(VisualCellsABC):
    '''
    Abstract base class of all animation classes.

    Instances of this class animate the spatial distribution of modelled
    variables (e.g., Vmem) over all time steps of the simulation.

    Attributes (Private)
    ----------
    _anim : FuncAnimation
        Low-level Matplotlib animation object instantiated by this high-level
        BETSE wrapper object.

    Attributes (Private: Time)
    ----------
    _time_step_count : int
        Number of frames to be plotted.
    _time_step_last : int
        0-based index of the last frame to be plotted, exactly equivalent to
        `self._time_step_count - 1`.
    _time_step : int
        0-based index of the frame currently being plotted, corresponding to
        the 0-based sampled time step currently being simulated.
    _time_step_absolute : int
        0-based index of the last frame to be plotted.

    Attributes (Private: Saving)
    ----------
    _save_frame_template : str
        :func:`str.format`-formatted template which, when formatted with the
        0-based index of the current frame, yields the absolute path of the
        image file to be saved for that frame.
    _writer_images : MovieWriter
        Matplotlib object saving animation frames as images if doing so _or_
        `None` otherwise.
    _writer_savefig_kwargs : dict
        Dictionary of all keyword arguments to be passed to the
        `Figure.savefig()` method called to save each animation frame for both
        images and video.
    _writer_video : MovieWriter
        Matplotlib object saving animation frames as video if doing so _or_
        `None` otherwise.

    Attributes (Private: Current)
    ----------
    _current_density_magnitude_time_series : ndarray
        Time series of all current density magnitudes (i.e., `Jmag_M`) if the
        optional `_init_current_density()` method has been called for
        this animation _or_ `None` otherwise.
    _current_density_x_time_series : list
        Time series of all current density X components if the optional
        `_init_current_density()` method has been called for this
        animation _or_ `None` otherwise.
    _current_density_y_time_series : list
        Time series of all current density Y components if the optional
        `_init_current_density()` method has been called for this
        animation _or_ `None` otherwise.
    _current_density_stream_plot : matplotlib.streamplot.StreamplotSet
        Streamplot of either electric current or concentration flux overlayed
        over this subclass' animation if `_is_overlaying_current` is
        `True` _or_ `None` otherwise.
    _is_overlaying_current : bool
        `True` if overlaying either electric current or concentration flux
        streamlines on this animation _or_ `False` otherwise. By design, this
        boolean is `True` if and only if the following are all also `True`:
        * The `p.I_overlay` boolean, implying the current simulation
          configuration to request current overlays.
        * The `p.calc_J` boolean, implying the current simulation
          configuration to model such currents.
        * The `is_current_overlayable` boolean parameter passed to the
          `__init__()` method of this class, implying the current animation to
          support current overlays.
    _is_current_overlay_only_gj : bool
        `True` only if overlaying intracellular current _or_ `False` otherwise
        (i.e., if overlaying both intra- and extracellular current). Ignored
        unless overlaying current (i.e., if `_is_overlaying_current` is `True`).
    '''

    # ..................{ LIFECYCLE                          }..................
    @type_check
    def __init__(
        self,

        # Mandatory parameters.
        is_current_overlayable: bool,
        save_dir_parent_basename: str,

        # Optional parameters.
        is_current_overlay_only_gj: (bool, NoneType) = None,
        is_ecm_required: bool = False,
        time_step_count: (int, NoneType) = None,
        *args, **kwargs
    ) -> None:
        '''
        Initialize this animation.

        Parameters
        ----------
        save_dir_parent_basename : str
            Basename of the parent directory of the subdirectory to which this
            animation's frames will be saved when requested by the current
            simulation configuration.
        is_current_overlayable : bool
            `True` if overlaying either electric current or concentration flux
            streamlines on this animation when requested by the current
            simulation configuration (as governed by the `p.I_overlay` and
            `p.calc_J` parameters) _or_ `False` otherwise. All subclasses
            except those already plotting streamlines (e.g., by calling the
            superclass :meth:`_plot_stream` method) should unconditionally
            enable this boolean.
        is_current_overlay_only_gj : optional[bool]
            `True` if only overlaying intracellular current _or_ `False` if
            overlaying both intra- and extracellular current. Ignored if
            current is _not_ being overlayed at all (i.e., if
            `_is_overlaying_current` is `False`). If `None`, defaults to the
            following state:
            * `False` if extracellular spaces are enabled _and_ both
               intracellular and extracellular current is to be animated.
            * `True` if either extracellular spaces are disabled _or_ are
               enabled but only intracellular current is to be animated.
        is_ecm_required : optional[bool]
            `True` if this animation is specific to extracellular spaces or
            `False` otherwise. If `True` and extracellular spaces are currently
            disabled, an exception is raised. Defaults to `False`.
        time_step_count : optional[int]
            Number of frames to be plotted. If `None`, defaults to the number
            of sampled time steps in the current tissue simulation.
        '''

        # Pass all parameters *NOT* listed above to our superclass.
        super().__init__(*args, **kwargs)

        # If this subclass requires extracellular spaces but extracellular
        # spaces are currently disabled, raise an exception.
        if is_ecm_required and not self.p.sim_ECM:
            raise BetseParametersException(
                'Animation "{}" requires extracellular spaces, which are '
                'disabled by the current simulation configuration.'.format(
                self._label))

        # Default unpassed parameters.
        if is_current_overlay_only_gj is None:
            is_current_overlay_only_gj = not (
                self.p.sim_ECM and self.p.IecmPlot)
        if time_step_count is None:
            time_step_count = len(self.sim.time)

        # Classify all remaining parameters.
        self._is_current_overlay_only_gj = is_current_overlay_only_gj
        self._time_step_count = time_step_count

        # 0-based index of the last frame to be plotted.
        self._time_step_last = self._time_step_count - 1

        # If this subclass requests a current overlay, do so only if:
        #
        # * Requested by the current simulation configuration via "p.I_overlay".
        # * This configuration is modelling currents via "p.calc_J".
        self._is_overlaying_current = (
            is_current_overlayable and self.p.I_overlay)

        # Type of animation attempt to be logged below.
        animation_verb = None
        if self._is_show:
            animation_verb = 'Plotting'
        elif self._is_save:
            animation_verb = 'Saving'
        # If neither displaying nor saving this animation, this animation would
        # ideally reduce to a noop. Since this is a superclass method, however,
        # simply returning would have little effect; while raising an exception
        # would certainly have an effect, doing so would also require all
        # callers to explicitly catch and ignore that exception -- in which
        # case this object would hardly have reduced to a noop. In short,
        # ignoring this edge case is currently the only sane policy.

        # Log this animation as early as reasonably feasible.
        if animation_verb is not None:
            logs.log_info(
                '%s animation "%s"...', animation_verb, self._label)

        # Classify attributes to be possibly redefined below.
        self._current_density_magnitude_time_series = None
        self._current_density_x_time_series = None
        self._current_density_y_time_series = None
        self._current_density_stream_plot = None
        self._writer_images = None
        self._writer_video = None

        # 0-based index of the current frame.
        self._time_step = 0

        # If saving animations, prepare to do so.
        self._init_saving(save_dir_parent_basename)

        # If overlaying current, prepare to do so.
        if self._is_overlaying_current:
            self._init_current_density()


    @type_check
    def _init_saving(self, save_dir_parent_basename: str) -> None:
        '''
        Initialize this animation for platform-compatible file saving if
        enabled by the current simulation configuration _or_ noop otherwise.

        Parameters
        ----------
        save_dir_parent_basename : str
            Basename of the parent directory of the subdirectory to which this
            animation's frames will be saved when requested by the current
            simulation configuration. Defaults to a suitably generic basename.
        '''

        # If this animation is unsaved, noop.
        if not self._is_save:
            return

        #FIXME: This is silly. Rather than prohibiting animation names
        #containing such separators, simply sanitize this animation's name by
        #globally replacing all such separators by non-separator characters
        #guaranteed to be permitted in pathnames for all platforms (e.g., "_"
        #or "-" characters).

        # If the human-readable name of this animation contains directory
        # separators and hence is *NOT* a valid basename, raise an exception.
        paths.die_unless_basename(self._label)

        #FIXME: !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #This is an utter travesty, but we have no choice but to hack detection
        #of the current loop type until we sort out just what is going on with
        #this boolean and/or string enumeration elsewhere.
        #FIXME: !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        if hasattr(self.p, 'plot_type'):
            plot_type = self.p.plot_type
        else:
            plot_type = 'sim' if self.p.run_sim else 'init'

        # Path of the phase-specific parent directory of the subdirectory to
        # which these files will be saved.
        loop_dirname = None
        if plot_type == 'sim':
            loop_dirname = self.p.sim_results
        elif plot_type == 'init':
            loop_dirname = self.p.init_results
        else:
            raise BetseParametersException(
                'Animation saving unsupported during the "{}" loop.'.format(
                    plot_type))

        # Animation configuration localized for convenience.
        anim_config = self.p.anim

        # If saving animation frames as either images or video, prepare to do
        # so in a manner common to both.
        if anim_config.is_images_save or anim_config.is_video_save:
            # Dictionary of all keyword arguments to be passed to the
            # `Figure.savefig()` method called to save each animation frame for
            # both images and video.
            self._writer_savefig_kwargs = {
                # Plot the background of each animation frame as transparent
                # rather than pure white.
                'transparent': True,
            }

            #FIXME: Refactor all calls to os.makedirs() everywhere similarly.

            # Path of the subdirectory to which these files will be saved,
            # creating this subdirectory and all parents thereof if needed.
            save_dirname = paths.join(
                loop_dirname, save_dir_parent_basename, self._label)
            save_dirname = dirs.canonicalize_and_make_unless_dir(save_dirname)

        # If saving animation frames as images, prepare to do so.
        if anim_config.is_images_save:
            #FIXME: This currently defaults to padding frames with six or seven
            #zeroes, on average. Let's make this a bit more aesthetic by
            #padding frames to only as many zeroes are absolutely required by
            #the current frame count. To do that, in turn, we'll probably need
            #to shift everything that follows in this method to the _animate()
            #method, where the actual frame count is finally passed.

            # Template expanding to the basename of each image to be saved.
            # The "ImageWriter" class subsequently expands the "{{"- and
            # "}}"-delimited substring to the 0-based index of the current
            # frame number.
            save_frame_template_basename = '{}_{{:07d}}.{}'.format(
                self._label, anim_config.image_filetype)

            # Template expanding to the absolute path of each image to be
            # saved.
            writer_images_template = paths.join(
                save_dirname, save_frame_template_basename)

            # Object writing animation frames as images.
            self._writer_images = ImageWriter()

            # Log this preparation.
            logs.log_debug(
                'Preparing to save animation frames "%s"...',
                writer_images_template)

            # Prepare to save these animation frames.
            self._writer_images.setup(
                fig=self._figure,
                outfile=writer_images_template,
                dpi=anim_config.image_dpi,
            )

        # If saving animation frames as video, prepare to do so.
        if anim_config.is_video_save:
            # Name of the first video encoder installed on the current system.
            video_writer_name = mplvideo.get_first_writer_name(
                anim_config.video_writer_names)
            # print('found video writer: {}'.format(VideoWriterClass))

            # Matplotlib animation writer class encapsulating this encoder.
            VideoWriterClass = mplvideo.get_writer_class(video_writer_name)

            # Name of the first video codec supported by both this video
            # encoder and the video container format corresponding to this
            # video's filetype.
            video_codec_name = mplvideo.get_first_codec_name(
                writer_name=video_writer_name,
                container_filetype=anim_config.video_filetype,
                codec_names=anim_config.video_codec_names,
            )

            # Basename of the video to be written.
            save_video_basename = '{}.{}'.format(
                self._label, anim_config.video_filetype)

            # Absolute path of the video to be written.
            writer_video_filename = paths.join(
                save_dirname, save_video_basename)

            # Object writing animation frames as video.
            self._writer_video = VideoWriterClass(
                bitrate=anim_config.video_bitrate,
                codec=video_codec_name,
                fps=anim_config.video_framerate,
                metadata=anim_config.video_metadata,
            )

            # Log this preparation.
            logs.log_debug(
                'Preparing to save animation video "%s"...',
                writer_video_filename)

            # Prepare to save this animation video. Matplotlib squelches
            # critical (technically non-fatal but effectively fatal)
            # warnings and errors emitted by the external command invoked
            # by this call to the MovieWriter.setup() method *UNLESS* the
            # current matplotlib-specific verbosity level is "debug".
            # Temporarily ensure this for the duration of this call.
            with mpl_config.verbosity_debug_if_helpful():
                self._writer_video.setup(
                    fig=self._figure,
                    outfile=writer_video_filename,
                    dpi=anim_config.video_dpi,
                )


    # This method has been overridden to support subclasses that manually
    # handle animations rather than calling the _animate() method (e.g., the
    # "AnimCellsWhileSolving" subclass).
    def _prep_figure(self, *args, **kwargs) -> None:

        super()._prep_figure(*args, **kwargs)

        # If overlaying current, do so.
        if self._is_overlaying_current:
            self._plot_current_density()

    # ..................{ ANIMATORS                          }..................
    @type_check
    def _animate(self, *args, **kwargs) -> None:
        '''
        Display and/or save this animation as requested by the current
        simulation configuration.

        This method is intended to be called as the last statement in the
        :meth:`__init__` method of all subclasses of this superclass.

        Parameters
        ----------
        All parameters are passed to the :meth:`_prep_figure` method.
        '''

        # Prepare for plotting immediately *BEFORE* plotting the first frame.
        self._prep_figure(*args, **kwargs)

        #FIXME: For efficiency, we should probably be passing "blit=True," to
        #FuncAnimation(). Unfortunately, doing so will necessitate
        #restructuring animations to conform to blitting-specific requirements,
        #including:
        #
        #* The definition of a new init_frame() method of this class, which
        #  plots all portions of this animation *NOT* changing between frames.
        #  Are there any? We have no idea. Axes ticks presumably never change
        #  between frames for any animation, so there should be *SOMETHING* to
        #  plot here.
        #* The passing of this method to the "FuncAnimation" instance defined
        #  below via the "init_func" parameter: e.g.,
        #      init_func=self.init_frame,
        #* Refactoring the plot_frame() method to return the tuple of all
        #  matplotlib artist objects modified for the current frame. This is
        #  probably infeasible in a generic manner given the current crusty
        #  design of this class, but should be trivial (...in theory) after
        #  redesigning this class to support composoble
        #
        #    http://devosoft.org/making-efficient-animations-in-matplotlib-with-blitting
        #
        #Lemon grass and dill!

        # Create and assign an animation function to a local variable. If the
        # latter is *NOT* done, this function will be garbage collected prior
        # to subsequent plot handling -- in which case only the first plot will
        # be plotted without explicit warning or error. Die, matplotlib! Die!!!
        self._anim = FuncAnimation(
            # Figure to which the "func" callable plots each frame.
            fig=self._figure,

            # Callable plotting each frame.
            func=self.plot_frame,

            # Number of frames to be animated.
            frames=self._time_step_count,

            #FIXME: The interval should, ideally, be synchronized with the FPS
            #used for video encoding. To guarantee this:
            #
            #* Generalize the FPS option in the configuration file to *ALL*
            #  animations. Currently, this option only applies to video
            #  encoding.
            #* Convert the currently configured FPS into this interval in
            #  milliseconds as follows:
            #
            #      interval = 1000.0 / fps

            # Delay in milliseconds between consecutive frames. To convert this
            # delay into the equivalent frames per second (FPS):
            #
            #      fps = 1000.0 / interval
            interval=200,

            #FIXME: This is a bit silly. Ideally, animations should *ALWAYS* be
            #repeatable. Once we've refactored away usage of the
            #Animation.save() method, refactor:
            #
            #* This parameter to unconditionally enable repeating: e.g.,
            #      repeat=True,
            #* The plot_frame() method to conditionally call MovieWriter
            #  methods (e.g., grab_frame(), finish()) *ONLY* if the current
            #  call to the plot_frame() method is the first such call for the
            #  current frame. While this state would be trivial for this class
            #  to record, perhaps matplotlib's "Animation" base class already
            #  records this state? Contemplate us up.

            # Indefinitely repeat this animation unless saving animations, as
            # doing so under the current implementation would repeatedly (and
            # hence unnecessarily) overwrite previously written files.
            repeat=not self._is_save,
        )

        try:
            # If displaying and optionally saving this animations, do so.
            if self._is_show:
                #FIXME: If the current backend is non-interactive (e.g.,
                #"Agg"), the following function call reduces to a noop. This is
                #insane, frankly. In this case, this animation's plot_frame()
                #is never called! No errors or warnings are logged, so it's
                #unclear who or what is the culprit here. If the pyplot.show()
                #function is indeed only supported by interactive backends, we
                #should do the following here:
                #
                #* Detect whether or not the current backend is
                #  non-interactive.
                #* If so, either:
                #  * Emit an explicit warning advising the user that this
                #    animation will almost certainly be silently ignored. This
                #    isn't terribly ideal, but it's better than zilch.
                #  * If this animation is currently being saved, simply perform
                #    the non-display save logic performed below -- which *DOES*
                #    behave as expected for non-interactive backends. Clearly,
                #    the culprit is the pyplot.show() function. Mournful sigh.

                # Display and optionally save this animations. Note that,
                # although this function is called in a blocking manner, the
                # GUI-driven event loops of some interactive backends appear to
                # ignore the request for blocking behavior and perform
                # non-blocking behaviour instead. This, in turn, prevents this
                # branch from reliably finalizing this animation by calling the
                # close() method. This differs from the non-interactive
                # saving-specific branch that follows, which is guaranteed to
                # behave in a blocking manner and hence *CAN* reliably call the
                # close() method. tl;dr: GUIs, so random.
                pyplot.show()
            # Else if only saving but not displaying this animation *AND* at
            # least one animation writer doing so is enabled, do so.
            elif self._is_save and (
                self._writer_images is not None or
                self._writer_video is not None
            ):
                # Save this animation by iteratively calling our plot_frame()
                # method to save each animation frame. Since this method
                # already manually saves each such frame for the case of both
                # displaying *AND* saving this animation via the above call to
                # the pyplot.show() function, that logic is reused here by
                # preventing this call to the Animation.save() method from
                # attempting to automatically save each such frame.
                #
                # By default, the Animation.save() method iteratively calls the
                # MovieWriter.grab_frame() method of the passed "writer" object
                # to save each such frame. If no such object is passed, this
                # object defaults to a new writer whose name is the current
                # value of the "animation.writer" rcparam. Hence, there exists
                # no means of preventing the Animation.save() method from
                # writing. However, there also exists no good alternative to
                # this method that iteratively calls our plot_frame() method
                # without also writing. For example:
                #
                # * The pyplot.show() function iterating frames silently
                #   reduces to a noop for non-interactive backends and is thus
                #   inapplicable as a general-purpose solution.
                # * The frame iteration automatically performed by the
                #   Animation.save() method is both non-trivial and requires
                #   calls to private methods of the matplotlib animation API.
                #   While this iteration could (and actually was, in the first
                #   implementation of this approach) be reduplicated here,
                #   doing so would be overly fragile and hence break under
                #   upstream changes to this private API.
                #
                # The robust solution is to instead pass the Animation.save()
                # method a writer reducing to a noop, circumventing conflicts
                # with the manual saving performed by our plot_frame() method.
                self._anim.save(
                    # Note that, since "NoopWriter" maintains no state, a
                    # singleton "NoopWriter" instance could technically be
                    # shared amongst all animation classes. However, since
                    # "NoopWriter" construction is trivially fast, there are no
                    # demonstrable advantages and arguable disadvantages to
                    # doing so (e.g., code complexity, space consumption).
                    writer=NoopWriter(),

                    # Pass an ignorable filename. To guarantee that an
                    # exception is raised on this method attempting to read or
                    # write this file, pass a filename guaranteed to be invalid
                    # on all supported platforms (e.g., containing null bytes).
                    # For understandable reasons, this parameter is mandatory.
                    filename=paths.INVALID_PATHNAME,
                )

                # Finalize saving this animation.
                self.close()

        # plt.show() unreliably raises exceptions on window close resembling:
        #     AttributeError: 'NoneType' object has no attribute 'tk'
        # This error appears to ignorable and hence is caught and squelched.
        except AttributeError as exc:
            # If this is that exception, mercilessly squelch it.
            if str(exc) == "'NoneType' object has no attribute 'tk'":
                pass
            # Else, reraise this exception.
            else:
                raise

    # ..................{ CLOSERS                            }..................
    def close(self) -> None:
        '''
        Finalize displaying and/or saving this non-blocking animation.

        This method is intended to be called as the last statement in the
        `_animate()` method animating this non-blocking subclass. If this
        subclass is blocking, this method must _not_ be called.

        See Also
        ----------
        close()
            Superclass method destroying this animation's low-level plot and
            all memory associated with this plot.
        '''

        # Finalize this animation's low-level plot.
        super().close()

        # Finalize all writers saving this animation if any.
        self._close_writers()

        # Prevent this animation from being reused and break hard cycles.
        self._anim = None


    def _close_writers(self) -> None:
        '''
        Finalize all writers saving this animation if any.
        '''

        # If saving animation frames as images...
        if self._writer_images is not None:
            # Finalize doing so.
            self._writer_images.finish()

            # Prevent this writer from being reused and break hard cycles.
            self._writer_images = None

        # If saving animation frames as video...
        if self._writer_video is not None:
            # Finalize doing so. For debuggability, temporarily escalate the
            # matplotlib-specific verbosity level.
            with mpl_config.verbosity_debug_if_helpful():
                self._writer_video.finish()

            # Prevent this writer from being reused and break hard cycles.
            self._writer_video = None

    # ..................{ PLOTTERS                           }..................
    #FIXME: Shift this method and similar methods called by this method (e.g.,
    #_plot_frame_axes_title()) into the "VisualCellsABC" superclass. When doing
    #so, consider renaming this method to visualize_time_step() for generality.
    #FIXME: Insanity. For "PlotAfterSolving"-style plots, the first frame is
    #uselessly plotted twice. Investigate, please.

    @type_check
    def plot_frame(self, time_step: int) -> None:
        '''
        Iterate this animation to the next frame.

        This method is iteratively called by Matplotlib's `FuncAnimation()`
        class instantiated by our `_animate()` method. The subclass
        implementation of this abstract method is expected to modify this
        animation's figure and axes so as to display the next frame. It is
        _not_, however, expected to save that figure to disk; frame saving is
        already implemented by this base class in a general-purpose manner.

        Specifically, this method (in order):

        . Calls the subclass :meth:`_plot_frame_figure` method to update the
          current figure with this frame's data.
        . Updates the current figure's axes title with the current time.
        . Optionally writes this frame to disk if desired.

        Parameters
        ----------
        time_step : int
            0-based index of the frame to be plotted _or_ -1 if the most recent
            frame is to be plotted.
        '''

        # Absolute 0-based index of the frame to be plotted.
        #
        # If the passed index is -1 and hence relative rather than absolute,
        # this index is assumed to be the last index of the current
        # simulation's array of time steps.
        if time_step == -1:
            time_step_absolute = len(self.sim.time) - 1
        # Else, the passed index is already absolute and hence used as is.
        else:
            time_step_absolute = time_step

        # Log this animation frame.
        logs.log_debug(
            'Plotting animation "%s" frame %d / %d...',
            self._label, time_step_absolute, self._time_step_last)

        # Classify this time step for subsequent access by subclasses.
        self._time_step = time_step

        # If plotting a current overlay, do so.
        if self._is_overlaying_current:
            #FIXME: Refactor _replot_current_density() to use
            #"self._time_step" rather than repass this parameter everywhere.
            self._replot_current_density(self._time_step)

        # Plot this frame's title *BEFORE* this frame, allowing axes changes
        # performed by the subclass implementation of the _plot_frame_figure()
        # method called below to override the default title.
        self._plot_frame_axes_title()

        # Plot this frame via external layers *BEFORE* plotting this frame
        # via subclass logic, allowing the latter to override the former.
        self._visualize_layers()

        # Plot this frame via subclass logic *AFTER* performing all
        # superclass-specific plotting.
        self._plot_frame_figure()

        # If saving this animation, save this frame.
        if self._is_save:
            # If saving animation frames as images, save this frame as such.
            if self._writer_images is not None:
                self._writer_images.grab_frame(**self._writer_savefig_kwargs)

            # If saving animation frames as video, save this frame as such.
            if self._writer_video is not None:
                # For debuggability, temporarily escalate the
                # matplotlib-specific verbosity level.
                with mpl_config.verbosity_debug_if_helpful():
                    self._writer_video.grab_frame(
                        **self._writer_savefig_kwargs)

            # If this is the last frame to be plotted, finalize all writers
            # *AFTER* instructing these writers to write this frame.
            if time_step_absolute == self._time_step_last:
                logs.log_debug(
                    'Finalizing animation "%s" saving...', self._label)
                self._close_writers()


    #FIXME: Update with support for time acceleration.
    def _plot_frame_axes_title(self) -> None:
        '''
        Plot the current frame title of this animation onto this animation's
        axes.

        By default, this title interpolates the current time step and must thus
        be replotted for each animation frame.
        '''

        #FIXME: Shift into a new "betse.util.time.times" submodule.

        # Number of seconds in a minute.
        SECONDS_PER_MINUTE = 60

        # Number of seconds in an hour.
        SECONDS_PER_HOUR = SECONDS_PER_MINUTE * 60

        #FIXME: For efficiency, classify the following local variables as
        #object attributes in the __init__() method rather than recompute these
        #variables each animation frame here.

        # Human-readable suffix of the units that simulation times are reported
        # in (e.g., "ms" for milliseconds).
        time_unit_suffix = None

        # Factor by which low-level simulation times are multiplied to yield
        # human-readable simulation times in the same units of
        # "time_unit_suffix".
        time_unit_factor = None

        # Duration in seconds of the current simulation phase (e.g., "init",
        # "run"), accelerated by the current gap junction acceleration factor.
        time_len = self.p.total_time_accelerated

        # If this phase runs for less than or equal to 100ms, report
        # simulation time in milliseconds (i.e., units of 0.001s).
        if time_len <= 0.1:
            time_unit_suffix = 'ms'
            time_unit_factor = 1e3
        # Else if this phase runs for less than or equal to one minute, report
        # simulation time in seconds (i.e., units of 1s).
        elif time_len <= SECONDS_PER_MINUTE:
            time_unit_suffix = 's'
            time_unit_factor = 1
        # Else if this phase runs for less than or equal to one hour, report
        # simulation time in minutes (i.e., units of 60s).
        elif time_len <= SECONDS_PER_HOUR:
            time_unit_suffix = ' minutes'
            time_unit_factor = 1/SECONDS_PER_MINUTE
        # Else, this phase is assumed to run for less than or equal to one day.
        # In this case, simulation time is reported in hours (i.e., units of
        # 60*60s).
        else:
            time_unit_suffix = ' hours'
            time_unit_factor = 1/SECONDS_PER_HOUR

        # Update this figure with the current time, rounded to one decimal
        # place for readability.
        self._axes.set_title('{} (time: {:.1f}{})'.format(
            self._axes_title,
            time_unit_factor * self.p.gj_acceleration * self.sim.time[self._time_step],
            time_unit_suffix,
        ))


    @abstractmethod
    def _plot_frame_figure(self) -> None:
        '''
        Plot the current frame of this animation onto this animation's figure.
        '''
        pass

    # ..................{ PRIVATE ~ plot : current           }..................
    def _init_current_density(self) -> None:
        '''
        Initialize all attributes pertaining to current density.

        Specifically, this method defines the `_current_density_x_time_series`,
        `_current_density_y_time_series`, and
        `_current_density_magnitude_time_series` attributes. These attributes
        are required both by this superclass for animating current overlays
        _and_ by current-specific subclasses.
        '''

        # Time series of all current density X and Y components.
        if self._is_current_overlay_only_gj is True:
            I_grid_x_time = []
            I_grid_y_time = []

            # Interpolate data from cell centres to the xy-grid.
            cell_centres = (
                self.cells.cell_centres[:, 0], self.cells.cell_centres[:, 1])
            cell_grid = (self.cells.X, self.cells.Y)

            for i in range(0, len(self.sim.I_cell_x_time)):
                I_gj_x = self.cells.maskECM * interpolate.griddata(
                    cell_centres,
                    self.sim.I_cell_x_time[i],
                    cell_grid,
                    fill_value=0,
                    method=self.p.interp_type,
                )
                I_grid_x_time.append(I_gj_x)

                I_gj_y = self.cells.maskECM * interpolate.griddata(
                    cell_centres,
                    self.sim.I_cell_y_time[i],
                    cell_grid,
                    fill_value=0,
                    method=self.p.interp_type,
                )
                I_grid_y_time.append(I_gj_y)

            self._current_density_x_time_series = I_grid_x_time
            self._current_density_y_time_series = I_grid_y_time

        else:
            self._current_density_x_time_series = self.sim.I_tot_x_time
            self._current_density_y_time_series = self.sim.I_tot_y_time

        # Time series of all current density magnitudes (i.e., `Jmag_M`),
        # multiplying by 100 to obtain current density in units of uA/cm2.
        self._current_density_magnitude_time_series = 100*np.sqrt(
            np.asarray(self._current_density_x_time_series) ** 2 +
            np.asarray(self._current_density_y_time_series) ** 2) + 1e-15


    def _plot_current_density(self) -> None:
        '''
        Overlay the first frame of this subclass' animation with a streamplot of
        either electric current or concentration flux.
        '''

        # If animating only intracellular current, do so.
        if self._is_current_overlay_only_gj:
            self._axes_title = 'Intracellular Current'

            # #FIXME: Is there any point to this? From what we can tell, the
            # #"self._current_density_stream_plot" will simply be outright
            # #replaced for the first and all subsequent frames. Galloping fish!
            # self._current_density_stream_plot, self._axes = cell_stream(
            #     self._current_density_x_time_series[-1],
            #     self._current_density_y_time_series[-1],
            #     self._axes, self.cells, self.p)
        # If animating both extracellular and intracellular current, do so.
        else:
            self._axes_title = 'Total Current Overlay'

            # #FIXME: Likewise.
            # self._current_density_stream_plot, self._axes = env_stream(
            #     self._current_density_x_time_series[-1],
            #     self._current_density_y_time_series[-1],
            #     self._axes, self.cells, self.p)
            #


    #FIXME: Replace all usage of the "frame_number" parameter with the existing
    #"self._time_step" variable; then remove this parameter.
    @type_check
    def _replot_current_density(self, frame_number: int) -> None:
        '''
        Overlay the passed frame of this subclass' animation with a streamplot
        of either electric current or concentration flux.

        Parameters
        -----------
        frame_number : int
            0-based index of the frame to be plotted.
        '''

        # Current density magnitudes for this frame.
        Jmag_M = self._current_density_magnitude_time_series[frame_number]

        # Erase the prior frame's overlay and streamplot this frame's overlay.
        self._current_density_stream_plot = self._plot_stream(
            old_stream_plot=self._current_density_stream_plot,
            x=self._current_density_x_time_series[frame_number] / Jmag_M,
            y=self._current_density_y_time_series[frame_number] / Jmag_M,
            magnitude=Jmag_M,
        )

# ....................{ SUBCLASSES                         }....................
#FIXME: Refactor as follows:
#
#* Rename the existing "anim" submodule of this subpackage to "animafter".
#* Define a new "animwhile" submodule of this subpackage.
#* Shift this and the following subclasses to the "animafter" submodule.
#* Shift the "AnimCellsWhileSolving" subclass to the "animwhile" submodule.
class AnimCellsAfterSolving(AnimCellsABC):
    '''
    Abstract base class of all post-simulation cell animation subclasses,
    animating simulation data over the cell cluster _after_ rather than
    _during_ simulation modelling.
    '''

    @type_check
    def __init__(
        self,
        p: 'betse.science.parameters.Parameters',
        *args, **kwargs
    ) -> None:
        '''
        Initialize this post-simulation animation.

        Parameters
        ----------
        p : Parameters
            Current simulation configuration.

        See the superclass `__init__()` method for all remaining parameters.
        '''

        # Initialize our superclass.
        super().__init__(
            # Pass this simulation configuration as is to our superclass.
            p=p,

            # Save and show this post-simulation animation only if this
            # configuration enables doing so.
            is_save=p.anim.is_after_sim_save,
            is_show=p.anim.is_after_sim_show,

            # Save all post-simulation animations to the same parent directory.
            save_dir_parent_basename='anim',

            # Pass all remaining arguments as is to our superclass.
            *args, **kwargs
        )


class AnimField(AnimCellsAfterSolving):
    '''
    Abstract base class of all animations of electric field strength plotted on
    the current cell cluster.

    Attributes
    ----------
    _magnitude_time_series : SequenceTypes
        Electric field magnitudes as a function of time.
    _mesh_plot : matplotlib.image.AxesImage
        Meshplot of the current or prior frame's electric field magnitude.
    _stream_plot : matplotlib.streamplot.StreamplotSet
        Streamplot of the current or prior frame's electric field.
    _x_time_series : SequenceTypes
        Electric field X components as a function of time.
    _y_time_series : SequenceTypes
        Electric field Y components as a function of time.
    _unit_x_time_series : SequenceTypes
        Electric field X unit components as a function of time. The resulting
        electric field vectors are **unit vectors** (i.e., have magnitude 1).
    _unit_y_time_series : SequenceTypes
        Electric field Y unit components as a function of time. The resulting
        electric field vectors are **unit vectors** (i.e., have magnitude 1).
    '''

    @type_check
    def __init__(
        self,
        x_time_series: SequenceTypes,
        y_time_series: SequenceTypes,
        *args, **kwargs
    ) -> None:
        '''
        Initialize this animation.

        Parameters
        ----------
        x_time_series : SequenceTypes
            SequenceTypes (e.g., list, numpy array) of all electric field
            strength X components indexed by simulation time.
        y_time_series : SequenceTypes
            SequenceTypes (e.g., list, numpy array) of all electric field
            strength Y components indexed by simulation time.

        See the superclass `__init__()` method for all remaining parameters.
        '''

        # Pass all parameters *NOT* listed above to our superclass.
        super().__init__(
            # Since this class already plots a streamplot, prevent the
            # superclass from plotting another streamplot as an overlay.
            is_current_overlayable=False,
            *args, **kwargs)

        # Classify all remaining parameters.
        self._x_time_series = x_time_series
        self._y_time_series = y_time_series

        # Electric field magnitudes and X and Y unit components.
        self._magnitude_time_series = []
        self._unit_x_time_series = []
        self._unit_y_time_series = []

        # Prefer an alternative colormap.
        self._colormap = self.p.background_cm


class AnimVelocity(AnimCellsAfterSolving):
    '''
    Abstract base class of all animations of a velocity flow plotted on the
    current cell cluster.
    '''

    def __init__(self, *args, **kwargs) -> None:

        # Pass all parameters *NOT* listed above to our superclass.
        super().__init__(
            # Since this class already plots a streamplot, prevent the
            # superclass from plotting another streamplot as an overlay.
            is_current_overlayable=False,
            *args, **kwargs)

        # Prefer an alternative colormap.
        self._colormap = self.p.background_cm